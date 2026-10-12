from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from .database import Base, engine, get_db
from . import models
from fastapi.middleware.cors import CORSMiddleware

from .schemas import (
    EventRequestCreate,
    EventRequestUpdate,
    EventRequestResponse,
    ProctorAssignmentCreate,
    ProctorReviewCreate,
    FinalDecisionCreate,
)
from .workflow import (
    validate_transition,
    SUBMITTED,
    UNDER_PROCTOR_REVIEW,
    PENDING_FINAL_DECISION,
    RETURNED,
    APPROVED,
    REJECTED,
    WITHDRAWN,
)

app = FastAPI(
    title="Permitrix API",
    description="Event request and approval workflow",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)


@app.get("/")
def home():
    return {
        "message": "Welcome to Permitrix API",
        "status": "running",
    }


@app.get("/health")
def health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return {"status": "healthy", "database": "connected"}


# 1. Create a new event request
@app.post(
    "/requests",
    response_model=EventRequestResponse,
    status_code=201,
)
def create_request(
    data: EventRequestCreate,
    db: Session = Depends(get_db),
):
    if data.end_date < data.start_date:
        raise HTTPException(
            status_code=422,
            detail="End date cannot be before start date.",
        )

    request = models.EventRequest(
        **data.model_dump(),
        reference_no=f"PR-{uuid4().hex[:10].upper()}",
        status="Draft",
    )

    db.add(request)
    db.commit()
    db.refresh(request)

    return request


# 2. View all requests, optionally filtered by student
@app.get("/requests", response_model=list[EventRequestResponse])
def list_requests(
    student_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(models.EventRequest)

    if student_id:
        query = query.filter(
            models.EventRequest.student_id == student_id
        )

    return query.order_by(
        models.EventRequest.id.desc()
    ).all()


# 3. View one request
@app.get(
    "/requests/{request_id}",
    response_model=EventRequestResponse,
)
def get_request(
    request_id: int,
    db: Session = Depends(get_db),
):
    request = db.get(models.EventRequest, request_id)

    if request is None:
        raise HTTPException(
            status_code=404,
            detail="Event request not found.",
        )

    return request


# 4. Update a draft request
@app.put(
    "/requests/{request_id}",
    response_model=EventRequestResponse,
)
def update_request(
    request_id: int,
    data: EventRequestUpdate,
    db: Session = Depends(get_db),
):
    request = db.get(models.EventRequest, request_id)

    if request is None:
        raise HTTPException(
            status_code=404,
            detail="Event request not found.",
        )

    if request.status != "Draft":
        raise HTTPException(
            status_code=400,
            detail="Only draft requests can be edited.",
        )

    changes = data.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one field to update.",
        )

    required_fields = {
        "event_title", "organizer", "category", "venue",
        "city", "start_date", "end_date", "purpose",
        "expected_benefit",
    }

    for field, value in changes.items():
        if field in required_fields and value is None:
            raise HTTPException(
                status_code=422,
                detail=f"{field} cannot be null.",
            )

    new_start = changes.get("start_date", request.start_date)
    new_end = changes.get("end_date", request.end_date)

    if new_end < new_start:
        raise HTTPException(
            status_code=422,
            detail="End date cannot be before start date.",
        )

    for field, value in changes.items():
        setattr(request, field, value)

    db.commit()
    db.refresh(request)

    return request


# 5. Submit a draft for proctor review
@app.post(
    "/requests/{request_id}/submit",
    response_model=EventRequestResponse,
)
def submit_request(
    request_id: int,
    db: Session = Depends(get_db),
):
    request = db.get(models.EventRequest, request_id)

    if request is None:
        raise HTTPException(
            status_code=404,
            detail="Event request not found.",
        )

    if request.status != "Draft":
        raise HTTPException(
            status_code=400,
            detail="Only draft requests can be submitted.",
        )

    request.status = "Submitted"
    request.submitted_at = datetime.now(timezone.utc)

    db.add(
        models.AuditLog(
            request_id=request.id,
            actor_id=request.student_id,
            action="RequestSubmitted",
            previous_status="Draft",
            new_status="Submitted",
            remarks="Student submitted event request for review.",
        )
    )

    db.commit()
    db.refresh(request)

    return request

    
# 6. Assign a submitted request to a proctor
@app.post("/requests/{request_id}/assign-proctor")
def assign_proctor(
    request_id: int,
    data: ProctorAssignmentCreate,
    db: Session = Depends(get_db),
):
    request = db.get(models.EventRequest, request_id)

    if request is None:
        raise HTTPException(
            status_code=404,
            detail="Event request not found.",
        )

    validate_transition(request.status, UNDER_PROCTOR_REVIEW)

    if not data.proctor_id.strip():
        raise HTTPException(
            status_code=422,
            detail="Proctor ID cannot be empty.",
        )

    previous_status = request.status

    assignment = models.ProctorAssignment(
        request_id=request.id,
        proctor_id=data.proctor_id.strip(),
    )

    request.status = UNDER_PROCTOR_REVIEW

    db.add(assignment)
    db.add(
        models.AuditLog(
            request_id=request.id,
            actor_id="SYSTEM",
            action="ProctorAssigned",
            previous_status=previous_status,
            new_status=UNDER_PROCTOR_REVIEW,
            remarks=f"Assigned proctor: {data.proctor_id.strip()}",
        )
    )

    try:
        db.commit()
        db.refresh(request)
    except Exception:
        db.rollback()
        raise

    return {
        "message": "Proctor assigned successfully.",
        "request_id": request.id,
        "proctor_id": data.proctor_id.strip(),
        "status": request.status,
    }


# 7. Record a proctor's recommendation
@app.post("/requests/{request_id}/proctor-review")
def proctor_review(
    request_id: int,
    data: ProctorReviewCreate,
    db: Session = Depends(get_db),
):
    request = db.get(models.EventRequest, request_id)

    if request is None:
        raise HTTPException(
            status_code=404,
            detail="Event request not found.",
        )

    if request.status != UNDER_PROCTOR_REVIEW:
        raise HTTPException(
            status_code=400,
            detail="Request must be under proctor review.",
        )

    assignment = (
        db.query(models.ProctorAssignment)
        .filter(
            models.ProctorAssignment.request_id == request_id,
            models.ProctorAssignment.proctor_id == data.proctor_id,
        )
        .order_by(models.ProctorAssignment.id.desc())
        .first()
    )

    if assignment is None:
        raise HTTPException(
            status_code=403,
            detail="This proctor is not assigned to the request.",
        )

    if data.recommendation == "Return":
        new_status = RETURNED
    else:
        new_status = PENDING_FINAL_DECISION

    validate_transition(request.status, new_status)

    previous_status = request.status

    review = models.ProctorReview(
        request_id=request.id,
        proctor_id=data.proctor_id,
        recommendation=data.recommendation,
        remarks=data.remarks,
    )

    request.status = new_status

    db.add(review)
    db.add(
        models.AuditLog(
            request_id=request.id,
            actor_id=data.proctor_id,
            action="ProctorReviewSubmitted",
            previous_status=previous_status,
            new_status=new_status,
            remarks=data.recommendation,
        )
    )

    try:
        db.commit()
        db.refresh(request)
    except Exception:
        db.rollback()
        raise

    return {
        "message": "Proctor recommendation recorded successfully.",
        "request_id": request.id,
        "recommendation": data.recommendation,
        "status": request.status,
    }


# 8. Make the final decision as the in-charge
@app.post("/requests/{request_id}/final-decision")
def make_final_decision(
    request_id: int,
    data: FinalDecisionCreate,
    db: Session = Depends(get_db),
):
    request = db.get(models.EventRequest, request_id)

    if request is None:
        raise HTTPException(
            status_code=404,
            detail="Event request not found.",
        )

    if request.status != PENDING_FINAL_DECISION:
        raise HTTPException(
            status_code=400,
            detail="Request must be pending final decision.",
        )

    if data.decision == "Rejected" and (
        data.reason is None or not data.reason.strip()
    ):
        raise HTTPException(
            status_code=422,
            detail="A reason is required when rejecting a request.",
        )

    validate_transition(request.status, data.decision)

    previous_status = request.status
    request.status = data.decision

    decision = models.FinalDecision(
        request_id=request.id,
        incharge_id=data.incharge_id,
        decision=data.decision,
        reason=data.reason.strip() if data.reason else None,
    )

    db.add(decision)
    db.add(
        models.AuditLog(
            request_id=request.id,
            actor_id=data.incharge_id,
            action="FinalDecisionMade",
            previous_status=previous_status,
            new_status=data.decision,
            remarks=data.reason,
        )
    )

    try:
        db.commit()
        db.refresh(request)
    except Exception:
        db.rollback()
        raise

    return {
        "message": "Final decision recorded successfully.",
        "request_id": request.id,
        "decision": data.decision,
        "status": request.status,
    }


# 9. Withdraw an event request
@app.post("/requests/{request_id}/withdraw")
def withdraw_request(
    request_id: int,
    student_id: str = Query(...),
    db: Session = Depends(get_db),
):
    request = db.get(models.EventRequest, request_id)

    if request is None:
        raise HTTPException(
            status_code=404,
            detail="Event request not found.",
        )

    if request.student_id != student_id:
        raise HTTPException(
            status_code=403,
            detail="You cannot withdraw another student's request.",
        )

    validate_transition(request.status, WITHDRAWN)

    previous_status = request.status
    request.status = WITHDRAWN

    db.add(
        models.AuditLog(
            request_id=request.id,
            actor_id=student_id,
            action="RequestWithdrawn",
            previous_status=previous_status,
            new_status=WITHDRAWN,
            remarks="Student withdrew the event request.",
        )
    )

    try:
        db.commit()
        db.refresh(request)
    except Exception:
        db.rollback()
        raise

    return {
        "message": "Event request withdrawn successfully.",
        "request_id": request.id,
        "status": request.status,
    }
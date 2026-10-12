
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from .database import Base, engine, get_db
from . import models
from .schemas import (
    EventRequestCreate,
    EventRequestUpdate,
    EventRequestResponse,
)

app = FastAPI(
    title="Permitrix API",
    description="Event request and approval workflow",
    version="1.0.0",
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
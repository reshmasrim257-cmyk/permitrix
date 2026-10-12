
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date,
    DateTime,
    ForeignKey,
    CheckConstraint,
    func,
)

from .database import Base


class EventRequest(Base):
    __tablename__ = "event_requests"

    id = Column(Integer, primary_key=True, index=True)
    reference_no = Column(String(30), unique=True, nullable=False, index=True)
    student_id = Column(String(100), nullable=False, index=True)
    event_title = Column(String(200), nullable=False)
    organizer = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    venue = Column(String(200), nullable=False)
    city = Column(String(100), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    event_url = Column(String(500), nullable=True)
    purpose = Column(Text, nullable=False)
    expected_benefit = Column(Text, nullable=False)
    supporting_document = Column(String(500), nullable=True)
    status = Column(String(40), nullable=False, default="Draft", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    submitted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_event_dates"),
    )


class ProctorAssignment(Base):
    __tablename__ = "proctor_assignments"

    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("event_requests.id"), nullable=False, index=True)
    proctor_id = Column(String(100), nullable=False, index=True)
    assigned_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ProctorReview(Base):
    __tablename__ = "proctor_reviews"

    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("event_requests.id"), nullable=False, index=True)
    proctor_id = Column(String(100), nullable=False, index=True)
    recommendation = Column(String(30), nullable=False)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "recommendation IN ('RecommendApproval', 'RecommendRejection', 'Return')",
            name="ck_proctor_recommendation",
        ),
    )


class FinalDecision(Base):
    __tablename__ = "final_decisions"

    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("event_requests.id"), nullable=False, index=True)
    incharge_id = Column(String(100), nullable=False, index=True)
    decision = Column(String(20), nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("decision IN ('Approved', 'Rejected')", name="ck_final_decision"),
        CheckConstraint(
            "decision != 'Rejected' OR "
            "(reason IS NOT NULL AND length(trim(reason)) > 0)",
            name="ck_rejection_reason",
        ),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("event_requests.id"), nullable=False, index=True)
    actor_id = Column(String(100), nullable=False, index=True)
    action = Column(String(100), nullable=False)
    previous_status = Column(String(40), nullable=True)
    new_status = Column(String(40), nullable=True)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

from datetime import date

from pydantic import BaseModel, ConfigDict


class EventRequestCreate(BaseModel):
    student_id: str
    event_title: str
    organizer: str
    category: str
    venue: str
    city: str
    start_date: date
    end_date: date
    event_url: str | None = None
    purpose: str
    expected_benefit: str
    supporting_document: str | None = None


class EventRequestUpdate(BaseModel):
    event_title: str | None = None
    organizer: str | None = None
    category: str | None = None
    venue: str | None = None
    city: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    event_url: str | None = None
    purpose: str | None = None
    expected_benefit: str | None = None
    supporting_document: str | None = None


class EventRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference_no: str
    student_id: str
    event_title: str
    organizer: str
    category: str
    venue: str
    city: str
    start_date: date
    end_date: date
    event_url: str | None = None
    purpose: str
    expected_benefit: str
    supporting_document: str | None = None
    status: str

from typing import Literal


class ProctorAssignmentCreate(BaseModel):
    proctor_id: str


class ProctorReviewCreate(BaseModel):
    proctor_id: str
    recommendation: Literal[
        "RecommendApproval",
        "RecommendRejection",
        "Return",
    ]
    remarks: str | None = None


class FinalDecisionCreate(BaseModel):
    incharge_id: str
    decision: Literal["Approved", "Rejected"]
    reason: str | None = None
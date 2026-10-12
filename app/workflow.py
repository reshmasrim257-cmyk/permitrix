
from fastapi import HTTPException

# Canonical request statuses
DRAFT = "Draft"
SUBMITTED = "Submitted"
UNDER_PROCTOR_REVIEW = "Under Proctor Review"
PENDING_FINAL_DECISION = "Pending Final Decision"
RETURNED = "Returned"
APPROVED = "Approved"
REJECTED = "Rejected"
WITHDRAWN = "Withdrawn"

# A transition is permitted only when explicitly listed here.
ALLOWED_TRANSITIONS = {
    DRAFT: {SUBMITTED, WITHDRAWN},
    SUBMITTED: {UNDER_PROCTOR_REVIEW, WITHDRAWN},
    UNDER_PROCTOR_REVIEW: {
        PENDING_FINAL_DECISION,
        RETURNED,
    },
    PENDING_FINAL_DECISION: {
        APPROVED,
        REJECTED,
        RETURNED,
    },
    RETURNED: {DRAFT, WITHDRAWN},
    APPROVED: set(),
    REJECTED: set(),
    WITHDRAWN: set(),
}


def validate_transition(current_status: str, new_status: str) -> None:
    """Reject status changes that are not allowed."""
    allowed = ALLOWED_TRANSITIONS.get(current_status, set())

    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Transition from '{current_status}' "
                f"to '{new_status}' is not allowed."
            ),
        )
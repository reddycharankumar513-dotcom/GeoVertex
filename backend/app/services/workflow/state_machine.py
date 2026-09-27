"""Controlled State Machine for Service Requests and Cases."""

from typing import Dict, List, Optional, Set, Tuple
from app.models.workflow import RequestStatus
from app.models.user import UserRole


class WorkflowStateError(Exception):
    """Raised when an illegal workflow state transition is attempted."""
    pass


class WorkflowStateMachine:
    """Deterministic state machine governing lifecycle transitions of service requests."""

    # Allowed transitions: source_status -> set of allowed destination_statuses
    VALID_TRANSITIONS: Dict[RequestStatus, Set[RequestStatus]] = {
        RequestStatus.DRAFT: {RequestStatus.SUBMITTED, RequestStatus.CANCELLED},
        RequestStatus.SUBMITTED: {RequestStatus.ACKNOWLEDGED, RequestStatus.ASSIGNED, RequestStatus.REJECTED, RequestStatus.CANCELLED},
        RequestStatus.ACKNOWLEDGED: {RequestStatus.ASSIGNED, RequestStatus.UNDER_REVIEW, RequestStatus.IN_PROGRESS, RequestStatus.REJECTED, RequestStatus.CANCELLED},
        RequestStatus.ASSIGNED: {RequestStatus.IN_PROGRESS, RequestStatus.UNDER_REVIEW, RequestStatus.CANCELLED},
        RequestStatus.IN_PROGRESS: {RequestStatus.UNDER_REVIEW, RequestStatus.WAITING_FOR_CITIZEN, RequestStatus.REVISION_REQUIRED, RequestStatus.APPROVED, RequestStatus.REJECTED, RequestStatus.CANCELLED},
        RequestStatus.WAITING_FOR_CITIZEN: {RequestStatus.RESUBMITTED, RequestStatus.CANCELLED},
        RequestStatus.REVISION_REQUIRED: {RequestStatus.RESUBMITTED, RequestStatus.CANCELLED},
        RequestStatus.RESUBMITTED: {RequestStatus.UNDER_REVIEW, RequestStatus.IN_PROGRESS},
        RequestStatus.UNDER_REVIEW: {RequestStatus.APPROVED, RequestStatus.REVISION_REQUIRED, RequestStatus.WAITING_FOR_CITIZEN, RequestStatus.REJECTED, RequestStatus.CANCELLED},
        RequestStatus.APPROVED: {RequestStatus.COMPLETED},
        RequestStatus.COMPLETED: set(),  # Terminal state
        RequestStatus.REJECTED: set(),   # Terminal state
        RequestStatus.CANCELLED: set(),  # Terminal state
    }

    # Role permissions for initiating transitions
    ROLE_TRANSITIONS: Dict[Tuple[RequestStatus, RequestStatus], Set[str]] = {
        (RequestStatus.DRAFT, RequestStatus.SUBMITTED): {"CITIZEN", "ADMIN"},
        (RequestStatus.DRAFT, RequestStatus.CANCELLED): {"CITIZEN", "ADMIN"},
        (RequestStatus.SUBMITTED, RequestStatus.ACKNOWLEDGED): {"GOVERNMENT_OFFICER", "ADMIN"},
        (RequestStatus.SUBMITTED, RequestStatus.ASSIGNED): {"GOVERNMENT_OFFICER", "ADMIN"},
        (RequestStatus.SUBMITTED, RequestStatus.REJECTED): {"GOVERNMENT_OFFICER", "ADMIN"},
        (RequestStatus.SUBMITTED, RequestStatus.CANCELLED): {"CITIZEN", "GOVERNMENT_OFFICER", "ADMIN"},
        (RequestStatus.ACKNOWLEDGED, RequestStatus.ASSIGNED): {"GOVERNMENT_OFFICER", "ADMIN"},
        (RequestStatus.ACKNOWLEDGED, RequestStatus.UNDER_REVIEW): {"GOVERNMENT_OFFICER", "ADMIN"},
        (RequestStatus.ACKNOWLEDGED, RequestStatus.IN_PROGRESS): {"GOVERNMENT_OFFICER", "ADMIN", "SURVEYOR"},
        (RequestStatus.ACKNOWLEDGED, RequestStatus.REJECTED): {"GOVERNMENT_OFFICER", "ADMIN"},
        (RequestStatus.ACKNOWLEDGED, RequestStatus.CANCELLED): {"CITIZEN", "GOVERNMENT_OFFICER", "ADMIN"},
        (RequestStatus.ASSIGNED, RequestStatus.IN_PROGRESS): {"GOVERNMENT_OFFICER", "ADMIN", "SURVEYOR"},
        (RequestStatus.ASSIGNED, RequestStatus.UNDER_REVIEW): {"GOVERNMENT_OFFICER", "ADMIN"},
        (RequestStatus.ASSIGNED, RequestStatus.CANCELLED): {"GOVERNMENT_OFFICER", "ADMIN"},
        (RequestStatus.IN_PROGRESS, RequestStatus.UNDER_REVIEW): {"GOVERNMENT_OFFICER", "ADMIN", "SURVEYOR"},
        (RequestStatus.IN_PROGRESS, RequestStatus.WAITING_FOR_CITIZEN): {"GOVERNMENT_OFFICER", "ADMIN"},
        (RequestStatus.IN_PROGRESS, RequestStatus.REVISION_REQUIRED): {"GOVERNMENT_OFFICER", "ADMIN"},
        (RequestStatus.IN_PROGRESS, RequestStatus.APPROVED): {"GOVERNMENT_OFFICER", "ADMIN"},
        (RequestStatus.IN_PROGRESS, RequestStatus.REJECTED): {"GOVERNMENT_OFFICER", "ADMIN"},
        (RequestStatus.IN_PROGRESS, RequestStatus.CANCELLED): {"GOVERNMENT_OFFICER", "ADMIN"},
        (RequestStatus.WAITING_FOR_CITIZEN, RequestStatus.RESUBMITTED): {"CITIZEN", "ADMIN"},
        (RequestStatus.WAITING_FOR_CITIZEN, RequestStatus.CANCELLED): {"CITIZEN", "ADMIN"},
        (RequestStatus.REVISION_REQUIRED, RequestStatus.RESUBMITTED): {"CITIZEN", "ADMIN"},
        (RequestStatus.REVISION_REQUIRED, RequestStatus.CANCELLED): {"CITIZEN", "ADMIN"},
        (RequestStatus.RESUBMITTED, RequestStatus.UNDER_REVIEW): {"GOVERNMENT_OFFICER", "ADMIN"},
        (RequestStatus.RESUBMITTED, RequestStatus.IN_PROGRESS): {"GOVERNMENT_OFFICER", "ADMIN", "SURVEYOR"},
        (RequestStatus.UNDER_REVIEW, RequestStatus.APPROVED): {"GOVERNMENT_OFFICER", "ADMIN"},
        (RequestStatus.UNDER_REVIEW, RequestStatus.REVISION_REQUIRED): {"GOVERNMENT_OFFICER", "ADMIN"},
        (RequestStatus.UNDER_REVIEW, RequestStatus.WAITING_FOR_CITIZEN): {"GOVERNMENT_OFFICER", "ADMIN"},
        (RequestStatus.UNDER_REVIEW, RequestStatus.REJECTED): {"GOVERNMENT_OFFICER", "ADMIN"},
        (RequestStatus.UNDER_REVIEW, RequestStatus.CANCELLED): {"GOVERNMENT_OFFICER", "ADMIN"},
        (RequestStatus.APPROVED, RequestStatus.COMPLETED): {"GOVERNMENT_OFFICER", "ADMIN"},
    }

    @classmethod
    def can_transition(
        cls,
        current_status: RequestStatus,
        target_status: RequestStatus,
        actor_role: str,
    ) -> bool:
        """Check if transition is structurally valid and actor has role authorization."""
        if target_status not in cls.VALID_TRANSITIONS.get(current_status, set()):
            return False
        return actor_role in cls.ROLE_TRANSITIONS.get((current_status, target_status), set())

    @classmethod
    def validate_transition(
        cls,
        current_status: RequestStatus,
        target_status: RequestStatus,
        actor_role: str,
        reason: Optional[str] = None,
    ) -> None:
        """Validate if transition from current to target status is valid and permitted for actor."""
        # 1. Structural validity check
        allowed_targets = cls.VALID_TRANSITIONS.get(current_status, set())
        if target_status not in allowed_targets:
            raise WorkflowStateError(
                f"Invalid workflow transition from '{current_status.value}' to '{target_status.value}'. "
                f"Allowed destinations: {[s.value for s in allowed_targets]}"
            )

        # 2. RBAC check
        transition_key = (current_status, target_status)
        allowed_roles = cls.ROLE_TRANSITIONS.get(transition_key, set())
        if actor_role not in allowed_roles:
            raise WorkflowStateError(
                f"Role '{actor_role}' is not authorized to transition request from "
                f"'{current_status.value}' to '{target_status.value}'. Required: {list(allowed_roles)}"
            )

        # 3. Mandatory reason checks
        if target_status == RequestStatus.REJECTED and (not reason or len(reason.strip()) < 5):
            raise WorkflowStateError("Rejection requires a documented reason (at least 5 characters).")

        if target_status == RequestStatus.REVISION_REQUIRED and (not reason or len(reason.strip()) < 5):
            raise WorkflowStateError("Requesting revision requires clear instructions for the citizen.")

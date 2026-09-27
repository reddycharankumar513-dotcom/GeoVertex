from typing import Dict, Set
from app.core.errors import BadRequestException, ConflictException


class SurveyStateMachine:
    """Enforces controlled lifecycle state transitions for survey assignments, sessions, and submissions."""

    # Valid Assignment State Transitions
    ASSIGNMENT_TRANSITIONS: Dict[str, Set[str]] = {
        "ASSIGNED": {"ACCEPTED", "IN_PROGRESS", "CANCELLED"},
        "ACCEPTED": {"IN_PROGRESS", "CANCELLED"},
        "IN_PROGRESS": {"SUBMITTED", "PAUSED", "CANCELLED"},
        "PAUSED": {"IN_PROGRESS", "CANCELLED"},
        "SUBMITTED": {"UNDER_REVIEW", "APPROVED", "REVISION_REQUIRED", "REJECTED"},
        "UNDER_REVIEW": {"APPROVED", "REVISION_REQUIRED", "REJECTED"},
        "REVISION_REQUIRED": {"IN_PROGRESS"},
        "APPROVED": set(),  # Terminal
        "REJECTED": set(),  # Terminal
        "CANCELLED": set(), # Terminal
    }

    # Valid Session State Transitions
    SESSION_TRANSITIONS: Dict[str, Set[str]] = {
        "DRAFT": {"ACTIVE", "COMPLETED"},
        "ACTIVE": {"PAUSED", "COMPLETED", "SUBMITTED", "SYNC_PENDING"},
        "PAUSED": {"ACTIVE", "COMPLETED"},
        "SYNC_PENDING": {"ACTIVE", "SYNCED", "COMPLETED"},
        "SYNCED": {"ACTIVE", "COMPLETED", "SUBMITTED"},
        "COMPLETED": {"SUBMITTED", "ACTIVE"},
        "SUBMITTED": set(), # Immutable terminal state for session
    }

    # Valid Submission State Transitions
    SUBMISSION_TRANSITIONS: Dict[str, Set[str]] = {
        "SUBMITTED": {"UNDER_REVIEW", "APPROVED", "REVISION_REQUIRED", "REJECTED"},
        "UNDER_REVIEW": {"APPROVED", "REVISION_REQUIRED", "REJECTED"},
        "REVISION_REQUIRED": set(), # Terminal for that version; next revision creates a new version
        "APPROVED": set(),          # Terminal
        "REJECTED": set(),          # Terminal
    }

    @classmethod
    def validate_assignment_transition(cls, current_status: str, next_status: str) -> None:
        """Validates that assignment status transition is legally permitted."""
        if current_status == next_status:
            return
        allowed = cls.ASSIGNMENT_TRANSITIONS.get(current_status, set())
        if next_status not in allowed:
            raise BadRequestException(
                f"Illegal assignment state transition from '{current_status}' to '{next_status}'. "
                f"Allowed target states: {', '.join(sorted(allowed)) if allowed else 'None (Terminal state)'}"
            )

    @classmethod
    def validate_session_transition(cls, current_status: str, next_status: str) -> None:
        """Validates that session status transition is legally permitted."""
        if current_status == next_status:
            return
        allowed = cls.SESSION_TRANSITIONS.get(current_status, set())
        if next_status not in allowed:
            raise BadRequestException(
                f"Illegal survey session state transition from '{current_status}' to '{next_status}'. "
                f"Allowed target states: {', '.join(sorted(allowed)) if allowed else 'None (Terminal state)'}"
            )

    @classmethod
    def validate_submission_transition(cls, current_status: str, next_status: str) -> None:
        """Validates that submission status transition is legally permitted."""
        if current_status == next_status:
            return
        allowed = cls.SUBMISSION_TRANSITIONS.get(current_status, set())
        if next_status not in allowed:
            raise BadRequestException(
                f"Illegal survey submission review state transition from '{current_status}' to '{next_status}'. "
                f"Allowed target states: {', '.join(sorted(allowed)) if allowed else 'None (Terminal state)'}"
            )


survey_state_machine = SurveyStateMachine()

"""SLA Tracking, Due Date Computation, and Escalation Rules."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional


class SLAEngine:
    """Calculates due dates, SLA compliance status, and escalation urgency."""

    @staticmethod
    def calculate_due_date(submitted_at: datetime, completion_sla_hours: int = 120) -> datetime:
        """Calculate target completion deadline based on submission time and SLA hours."""
        if submitted_at.tzinfo is None:
            submitted_at = submitted_at.replace(tzinfo=timezone.utc)
        return submitted_at + timedelta(hours=completion_sla_hours)

    @staticmethod
    def evaluate_status(
        due_at: Optional[datetime],
        completed_at: Optional[datetime] = None,
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Evaluate current SLA health: ON_TRACK, DUE_SOON (<= 24h), or OVERDUE."""
        if not due_at:
            return {
                "sla_status": "NOT_APPLICABLE",
                "is_overdue": False,
                "remaining_hours": None,
                "overdue_hours": 0.0,
            }

        if now is None:
            now = datetime.now(timezone.utc)
        elif now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        if due_at.tzinfo is None:
            due_at = due_at.replace(tzinfo=timezone.utc)

        # If already completed, check if it was completed on time
        if completed_at:
            if completed_at.tzinfo is None:
                completed_at = completed_at.replace(tzinfo=timezone.utc)
            was_on_time = completed_at <= due_at
            diff_hours = (completed_at - due_at).total_seconds() / 3600.0
            return {
                "sla_status": "COMPLETED_ON_TIME" if was_on_time else "COMPLETED_OVERDUE",
                "is_overdue": not was_on_time,
                "remaining_hours": 0.0,
                "overdue_hours": max(0.0, diff_hours),
            }

        diff_seconds = (due_at - now).total_seconds()
        diff_hours = diff_seconds / 3600.0

        if diff_seconds < 0:
            return {
                "sla_status": "OVERDUE",
                "is_overdue": True,
                "remaining_hours": 0.0,
                "overdue_hours": round(abs(diff_hours), 2),
            }
        elif diff_hours <= 24.0:
            return {
                "sla_status": "DUE_SOON",
                "is_overdue": False,
                "remaining_hours": round(diff_hours, 2),
                "overdue_hours": 0.0,
            }
        else:
            return {
                "sla_status": "ON_TRACK",
                "is_overdue": False,
                "remaining_hours": round(diff_hours, 2),
                "overdue_hours": 0.0,
            }

    @staticmethod
    def get_sla_status(due_at: Optional[datetime]):
        """Helper returning (sla_status, remaining_or_overdue_hours)."""
        res = SLAEngine.evaluate_status(due_at)
        rem = res["remaining_hours"]
        if rem is None:
            return res["sla_status"], 0.0
        if res["is_overdue"]:
            return res["sla_status"], -res["overdue_hours"]
        return res["sla_status"], rem


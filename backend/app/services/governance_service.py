"""Phase 13 — System Governance & Data Integrity Service.

Provides aggregated governance metrics and automated integrity audits.
"""

from typing import Any, Dict, List
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditEvent
from app.models.versioning import EntityVersion, VersionStatus
from app.models.workflow import Notification
from app.repositories.audit_repository import audit_repository
from app.repositories.versioning_repository import entity_version_repository


class GovernanceService:
    async def get_dashboard_metrics(self, db: AsyncSession) -> Dict[str, Any]:
        audit_stats = await audit_repository.get_statistics(db)
        versioned_entities = await entity_version_repository.get_total_versioned_entities(db)

        # Version status counts
        v_status_q = select(EntityVersion.version_status, func.count(EntityVersion.id)).group_by(
            EntityVersion.version_status
        )
        v_status_res = await db.execute(v_status_q)
        version_status_counts = {row[0]: row[1] for row in v_status_res.all()}

        # Total versions
        total_v_q = select(func.count(EntityVersion.id))
        total_v_res = await db.execute(total_v_q)
        total_versions = total_v_res.scalar() or 0

        # Notifications health
        notif_status_q = select(Notification.status, func.count(Notification.id)).group_by(
            Notification.status
        )
        notif_status_res = await db.execute(notif_status_q)
        notification_counts = {row[0]: row[1] for row in notif_status_res.all()}

        # Recent audit events (last 10)
        recent_events, _ = await audit_repository.get_events_filtered(db, skip=0, limit=10)

        return {
            "audit": audit_stats,
            "versioning": {
                "total_versions": total_versions,
                "versioned_entities": versioned_entities,
                "by_status": version_status_counts,
            },
            "notifications": {
                "by_status": notification_counts,
                "total": sum(notification_counts.values()),
            },
            "recent_events": [
                {
                    "id": str(e.id),
                    "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                    "action": e.action,
                    "category": e.category,
                    "severity": e.severity,
                    "entity_type": e.entity_type,
                    "entity_id": e.entity_id,
                    "actor_user_id": str(e.actor_user_id) if e.actor_user_id else None,
                    "result": e.result,
                }
                for e in recent_events
            ],
        }

    async def verify_data_integrity(self, db: AsyncSession) -> Dict[str, Any]:
        """Runs automated consistency checks across version chains and audit trails."""
        issues: List[str] = []

        # Check 1: Find entities with multiple CURRENT versions
        multi_current_q = (
            select(
                EntityVersion.entity_type,
                EntityVersion.entity_id,
                func.count(EntityVersion.id).label("cnt"),
            )
            .where(EntityVersion.version_status == VersionStatus.CURRENT.value)
            .group_by(EntityVersion.entity_type, EntityVersion.entity_id)
            .having(func.count(EntityVersion.id) > 1)
        )
        multi_current_res = await db.execute(multi_current_q)
        multi_currents = multi_current_res.all()
        if multi_currents:
            for row in multi_currents:
                issues.append(
                    f"Entity {row[0]}:{row[1]} has {row[2]} CURRENT versions (expected max 1)."
                )

        # Check 2: Audit records without timestamp
        no_time_q = select(func.count(AuditEvent.id)).where(AuditEvent.timestamp.is_(None))
        no_time_res = await db.execute(no_time_q)
        no_time_count = no_time_res.scalar() or 0
        if no_time_count > 0:
            issues.append(f"Found {no_time_count} audit records with missing timestamp.")

        return {
            "status": "HEALTHY" if not issues else "ISSUES_FOUND",
            "issues_count": len(issues),
            "issues": issues,
            "disclaimer": "GeoVertex Technical Data Integrity Verification Report.",
        }


governance_service = GovernanceService()

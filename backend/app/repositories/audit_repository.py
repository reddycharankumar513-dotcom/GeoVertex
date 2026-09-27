"""Phase 13 — Immutable Audit Trail Repository.

Append-only storage and comprehensive query engine for security, cadastral,
and operational audit events.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditEvent, AuditCategory, AuditSeverity, AuditResult
from app.repositories.base import BaseRepository


def _sanitize_for_json(data: Any) -> Any:
    if data is None:
        return {}
    try:
        return json.loads(json.dumps(data, default=str))
    except Exception:
        return {}


class AuditRepository(BaseRepository[AuditEvent]):
    def __init__(self):
        super().__init__(AuditEvent)

    async def log_event(
        self,
        db: AsyncSession,
        action: str,
        entity_type: str,
        entity_id: str,
        actor_user_id: Optional[uuid.UUID] = None,
        actor_role: Optional[str] = None,
        organization_id: Optional[uuid.UUID] = None,
        jurisdiction_id: Optional[uuid.UUID] = None,
        category: str = AuditCategory.SYSTEM.value,
        severity: str = AuditSeverity.INFO.value,
        result: str = AuditResult.SUCCESS.value,
        entity_version_id: Optional[uuid.UUID] = None,
        request_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        workflow_id: Optional[uuid.UUID] = None,
        case_id: Optional[str] = None,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None,
        reason: Optional[str] = None,
        before_snapshot: Optional[Dict[str, Any]] = None,
        after_snapshot: Optional[Dict[str, Any]] = None,
        changed_fields: Optional[List[str]] = None,
        geometry_changed: bool = False,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Appends an immutable audit record to the persistent audit log."""
        safe_details = _sanitize_for_json(details) if details is not None else {}
        safe_before = _sanitize_for_json(before_snapshot) if before_snapshot is not None else {}
        safe_after = _sanitize_for_json(after_snapshot) if after_snapshot is not None else {}

        event = AuditEvent(
            id=uuid.uuid4(),
            event_id=str(uuid.uuid4()),
            action=action,
            category=category,
            severity=severity,
            result=result,
            entity_type=entity_type,
            entity_id=str(entity_id),
            entity_version_id=entity_version_id,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            organization_id=organization_id,
            jurisdiction_id=jurisdiction_id,
            request_id=request_id,
            correlation_id=correlation_id,
            workflow_id=workflow_id,
            case_id=case_id,
            source_type=source_type,
            source_id=source_id,
            reason=reason,
            before_snapshot=safe_before,
            after_snapshot=safe_after,
            changed_fields=changed_fields or [],
            geometry_changed=geometry_changed,
            ip_address=ip_address,
            user_agent=user_agent,
            details=safe_details,
        )
        db.add(event)
        await db.flush()
        return event

    async def get_by_id(self, db: AsyncSession, event_id: uuid.UUID) -> Optional[AuditEvent]:
        result = await db.execute(select(AuditEvent).where(AuditEvent.id == event_id))
        return result.scalars().first()

    async def get_events_filtered(
        self,
        db: AsyncSession,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        action: Optional[str] = None,
        category: Optional[str] = None,
        actor_user_id: Optional[uuid.UUID] = None,
        source_type: Optional[str] = None,
        workflow_id: Optional[uuid.UUID] = None,
        correlation_id: Optional[str] = None,
        case_id: Optional[str] = None,
        severity: Optional[str] = None,
        result: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[AuditEvent], int]:
        """Queries audit log events with multi-dimensional filtering and pagination."""
        query = select(AuditEvent)
        count_query = select(func.count(AuditEvent.id))

        filters = []
        if entity_type:
            filters.append(AuditEvent.entity_type == entity_type)
        if entity_id:
            filters.append(AuditEvent.entity_id == str(entity_id))
        if action:
            filters.append(AuditEvent.action == action)
        if category:
            filters.append(AuditEvent.category == category)
        if actor_user_id:
            filters.append(AuditEvent.actor_user_id == actor_user_id)
        if source_type:
            filters.append(AuditEvent.source_type == source_type)
        if workflow_id:
            filters.append(AuditEvent.workflow_id == workflow_id)
        if correlation_id:
            filters.append(AuditEvent.correlation_id == correlation_id)
        if case_id:
            filters.append(AuditEvent.case_id == case_id)
        if severity:
            filters.append(AuditEvent.severity == severity)
        if result:
            filters.append(AuditEvent.result == result)
        if date_from:
            filters.append(AuditEvent.timestamp >= date_from)
        if date_to:
            filters.append(AuditEvent.timestamp <= date_to)

        if filters:
            for f in filters:
                query = query.where(f)
                count_query = count_query.where(f)

        count_res = await db.execute(count_query)
        total = count_res.scalar() or 0

        res = await db.execute(
            query.order_by(desc(AuditEvent.timestamp)).offset(skip).limit(limit)
        )
        return list(res.scalars().all()), total

    async def get_statistics(self, db: AsyncSession) -> Dict[str, Any]:
        """Calculates audit trail health and category metrics."""
        total_q = select(func.count(AuditEvent.id))
        total_res = await db.execute(total_q)
        total = total_res.scalar() or 0

        # By Category
        cat_q = select(AuditEvent.category, func.count(AuditEvent.id)).group_by(AuditEvent.category)
        cat_res = await db.execute(cat_q)
        by_category = {row[0]: row[1] for row in cat_res.all()}

        # By Severity
        sev_q = select(AuditEvent.severity, func.count(AuditEvent.id)).group_by(AuditEvent.severity)
        sev_res = await db.execute(sev_q)
        by_severity = {row[0]: row[1] for row in sev_res.all()}

        # By Result
        res_q = select(AuditEvent.result, func.count(AuditEvent.id)).group_by(AuditEvent.result)
        res_res = await db.execute(res_q)
        by_result = {row[0]: row[1] for row in res_res.all()}

        # Distinct actors count
        actors_q = select(func.count(func.distinct(AuditEvent.actor_user_id)))
        actors_res = await db.execute(actors_q)
        distinct_actors = actors_res.scalar() or 0

        return {
            "total_events": total,
            "by_category": by_category,
            "by_severity": by_severity,
            "by_result": by_result,
            "distinct_actors": distinct_actors,
        }


audit_repository = AuditRepository()

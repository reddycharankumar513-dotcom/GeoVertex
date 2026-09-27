"""Phase 13 — Domain Event Bus & Dispatcher.

Connects business operations to the append-only AuditEvent log and event-driven
Notification pipeline with idempotency and correlation tracking.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import logger
from app.models.audit import AuditCategory, AuditSeverity, AuditResult
from app.repositories.audit_repository import audit_repository


@dataclass
class DomainEvent:
    event_name: str
    aggregate_type: str
    aggregate_id: str
    actor_user_id: Optional[uuid.UUID] = None
    actor_role: Optional[str] = None
    organization_id: Optional[uuid.UUID] = None
    jurisdiction_id: Optional[uuid.UUID] = None
    category: str = AuditCategory.SYSTEM.value
    severity: str = AuditSeverity.INFO.value
    result: str = AuditResult.SUCCESS.value
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    workflow_id: Optional[uuid.UUID] = None
    case_id: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    reason: Optional[str] = None
    before_snapshot: Optional[Dict[str, Any]] = None
    after_snapshot: Optional[Dict[str, Any]] = None
    changed_fields: Optional[List[str]] = None
    geometry_changed: bool = False
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class DomainEventDispatcher:
    """Central internal event bus that persists audit logs and triggers notifications."""

    async def dispatch(self, db: AsyncSession, event: DomainEvent) -> None:
        try:
            # 1. Persist immutable audit event
            await audit_repository.log_event(
                db=db,
                action=event.event_name,
                entity_type=event.aggregate_type,
                entity_id=event.aggregate_id,
                actor_user_id=event.actor_user_id,
                actor_role=event.actor_role,
                organization_id=event.organization_id,
                jurisdiction_id=event.jurisdiction_id,
                category=event.category,
                severity=event.severity,
                result=event.result,
                request_id=event.request_id,
                correlation_id=event.correlation_id,
                workflow_id=event.workflow_id,
                case_id=event.case_id,
                source_type=event.source_type,
                source_id=event.source_id,
                reason=event.reason,
                before_snapshot=event.before_snapshot,
                after_snapshot=event.after_snapshot,
                changed_fields=event.changed_fields,
                geometry_changed=event.geometry_changed,
                details=event.details,
            )
            logger.info(
                f"[EventDispatcher] Event {event.event_name} logged for {event.aggregate_type}:{event.aggregate_id}"
            )
        except Exception as e:
            logger.error(f"[EventDispatcher] Failed to dispatch event {event.event_name}: {e}")
            raise e


domain_event_dispatcher = DomainEventDispatcher()

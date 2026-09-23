import uuid
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditEvent
from app.repositories.base import BaseRepository


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
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
        )
        db.add(event)
        await db.flush()
        return event

    async def get_events_filtered(
        self,
        db: AsyncSession,
        entity_type: Optional[str] = None,
        action: Optional[str] = None,
        actor_user_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[AuditEvent], int]:
        query = select(AuditEvent)
        if entity_type:
            query = query.where(AuditEvent.entity_type == entity_type)
        if action:
            query = query.where(AuditEvent.action == action)
        if actor_user_id:
            query = query.where(AuditEvent.actor_user_id == actor_user_id)

        count_query = select(AuditEvent.id)
        if entity_type:
            count_query = count_query.where(AuditEvent.entity_type == entity_type)
        if action:
            count_query = count_query.where(AuditEvent.action == action)
        if actor_user_id:
            count_query = count_query.where(AuditEvent.actor_user_id == actor_user_id)

        count_res = await db.execute(count_query)
        total = len(count_res.scalars().all())

        result = await db.execute(
            query.order_by(AuditEvent.timestamp.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all()), total


audit_repository = AuditRepository()

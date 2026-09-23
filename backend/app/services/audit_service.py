import uuid
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditEvent
from app.repositories.audit_repository import audit_repository


class AuditService:
    async def list_events(
        self,
        db: AsyncSession,
        entity_type: Optional[str] = None,
        action: Optional[str] = None,
        actor_user_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[AuditEvent], int]:
        return await audit_repository.get_events_filtered(
            db=db,
            entity_type=entity_type,
            action=action,
            actor_user_id=actor_user_id,
            skip=skip,
            limit=limit,
        )


audit_service = AuditService()

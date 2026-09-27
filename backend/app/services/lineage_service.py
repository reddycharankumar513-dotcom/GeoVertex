"""Phase 13 — Entity Lineage & Provenance Service.

Tracks cross-entity relationships (splits, merges, replacements, migrations).
"""

import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.versioning import EntityLineage, LineageRelationship
from app.repositories.versioning_repository import entity_lineage_repository


class LineageService:
    """Manages lineage records representing spatial divisions, consolidations, and replacements."""

    async def record_lineage(
        self,
        db: AsyncSession,
        source_entity_type: str,
        source_entity_id: str,
        target_entity_type: str,
        target_entity_id: str,
        relationship_type: str,
        reason: Optional[str] = None,
        source_version_id: Optional[uuid.UUID] = None,
        target_version_id: Optional[uuid.UUID] = None,
        actor_user_id: Optional[uuid.UUID] = None,
        workflow_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EntityLineage:
        lineage = EntityLineage(
            id=uuid.uuid4(),
            source_entity_type=source_entity_type,
            source_entity_id=str(source_entity_id),
            source_version_id=source_version_id,
            target_entity_type=target_entity_type,
            target_entity_id=str(target_entity_id),
            target_version_id=target_version_id,
            relationship_type=relationship_type,
            reason=reason,
            actor_user_id=actor_user_id,
            workflow_id=workflow_id,
            metadata_json=metadata or {},
        )
        db.add(lineage)
        await db.flush()
        return lineage

    async def get_lineage(
        self, db: AsyncSession, entity_type: str, entity_id: str
    ) -> List[EntityLineage]:
        return await entity_lineage_repository.get_lineage_for_entity(
            db, entity_type=entity_type, entity_id=str(entity_id)
        )


lineage_service = LineageService()

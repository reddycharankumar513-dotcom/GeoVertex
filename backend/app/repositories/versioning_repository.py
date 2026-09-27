"""Phase 13 — Versioning & Lineage Repositories.

Provides atomic, concurrency-safe access to EntityVersion and EntityLineage records.
"""

import uuid
from typing import List, Optional, Tuple
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.versioning import EntityVersion, EntityLineage, VersionStatus
from app.repositories.base import BaseRepository


class EntityVersionRepository(BaseRepository[EntityVersion]):
    def __init__(self):
        super().__init__(EntityVersion)

    async def get_by_id(self, db: AsyncSession, version_id: uuid.UUID) -> Optional[EntityVersion]:
        result = await db.execute(select(EntityVersion).where(EntityVersion.id == version_id))
        return result.scalars().first()

    async def get_by_uuid(self, db: AsyncSession, version_uuid: str) -> Optional[EntityVersion]:
        result = await db.execute(select(EntityVersion).where(EntityVersion.version_uuid == version_uuid))
        return result.scalars().first()

    async def get_latest_version(
        self, db: AsyncSession, entity_type: str, entity_id: str
    ) -> Optional[EntityVersion]:
        query = (
            select(EntityVersion)
            .where(
                EntityVersion.entity_type == entity_type,
                EntityVersion.entity_id == entity_id,
            )
            .order_by(desc(EntityVersion.version_number))
            .limit(1)
        )
        result = await db.execute(query)
        return result.scalars().first()

    async def get_active_version(
        self, db: AsyncSession, entity_type: str, entity_id: str
    ) -> Optional[EntityVersion]:
        query = (
            select(EntityVersion)
            .where(
                EntityVersion.entity_type == entity_type,
                EntityVersion.entity_id == entity_id,
                EntityVersion.version_status == VersionStatus.CURRENT.value,
            )
            .order_by(desc(EntityVersion.version_number))
            .limit(1)
        )
        result = await db.execute(query)
        return result.scalars().first()

    async def get_version_by_number(
        self, db: AsyncSession, entity_type: str, entity_id: str, version_number: int
    ) -> Optional[EntityVersion]:
        query = select(EntityVersion).where(
            EntityVersion.entity_type == entity_type,
            EntityVersion.entity_id == entity_id,
            EntityVersion.version_number == version_number,
        )
        result = await db.execute(query)
        return result.scalars().first()

    async def get_versions_for_entity(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[EntityVersion], int]:
        count_q = (
            select(func.count(EntityVersion.id))
            .where(
                EntityVersion.entity_type == entity_type,
                EntityVersion.entity_id == entity_id,
            )
        )
        total_res = await db.execute(count_q)
        total = total_res.scalar() or 0

        query = (
            select(EntityVersion)
            .where(
                EntityVersion.entity_type == entity_type,
                EntityVersion.entity_id == entity_id,
            )
            .order_by(desc(EntityVersion.version_number))
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all()), total

    async def get_total_versioned_entities(self, db: AsyncSession) -> int:
        query = select(func.count(func.distinct(EntityVersion.entity_id)))
        result = await db.execute(query)
        return result.scalar() or 0


class EntityLineageRepository(BaseRepository[EntityLineage]):
    def __init__(self):
        super().__init__(EntityLineage)

    async def get_lineage_for_entity(
        self, db: AsyncSession, entity_type: str, entity_id: str
    ) -> List[EntityLineage]:
        query = (
            select(EntityLineage)
            .where(
                (
                    (EntityLineage.source_entity_type == entity_type)
                    & (EntityLineage.source_entity_id == entity_id)
                )
                | (
                    (EntityLineage.target_entity_type == entity_type)
                    & (EntityLineage.target_entity_id == entity_id)
                )
            )
            .order_by(desc(EntityLineage.created_at))
        )
        result = await db.execute(query)
        return list(result.scalars().all())


entity_version_repository = EntityVersionRepository()
entity_lineage_repository = EntityLineageRepository()

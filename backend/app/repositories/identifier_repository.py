"""Phase 12 — Identifier Repository: async DB access for all identifier engine entities."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import Base
from app.models.identifier import (
    IdentifierGenerationJob,
    IdentifierLineage,
    IdentifierScheme,
    IdentifierStatus,
    PropertyIdentifier,
)
from app.repositories.base import BaseRepository


class IdentifierSchemeRepository(BaseRepository[IdentifierScheme]):
    def __init__(self):
        super().__init__(IdentifierScheme)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[IdentifierScheme]:
        result = await db.execute(
            select(IdentifierScheme).where(IdentifierScheme.scheme_code == code)
        )
        return result.scalars().first()

    async def get_active(self, db: AsyncSession) -> Optional[IdentifierScheme]:
        result = await db.execute(
            select(IdentifierScheme)
            .where(IdentifierScheme.active == True)
            .order_by(IdentifierScheme.version.desc())
        )
        return result.scalars().first()

    async def list_all(self, db: AsyncSession) -> List[IdentifierScheme]:
        result = await db.execute(
            select(IdentifierScheme).order_by(IdentifierScheme.version.desc())
        )
        return list(result.scalars().all())


class PropertyIdentifierRepository(BaseRepository[PropertyIdentifier]):
    def __init__(self):
        super().__init__(PropertyIdentifier)

    async def get_by_value(self, db: AsyncSession, value: str) -> Optional[PropertyIdentifier]:
        result = await db.execute(
            select(PropertyIdentifier).where(PropertyIdentifier.identifier_value == value)
        )
        return result.scalars().first()

    async def get_by_token(self, db: AsyncSession, token: str) -> Optional[PropertyIdentifier]:
        result = await db.execute(
            select(PropertyIdentifier).where(PropertyIdentifier.verification_token == token)
        )
        return result.scalars().first()

    async def get_active_for_entity(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: str,
        scheme_id: Optional[uuid.UUID] = None,
    ) -> Optional[PropertyIdentifier]:
        q = select(PropertyIdentifier).where(
            and_(
                PropertyIdentifier.entity_type == entity_type,
                PropertyIdentifier.entity_id == str(entity_id),
                PropertyIdentifier.status == IdentifierStatus.ACTIVE.value,
            )
        )
        if scheme_id:
            q = q.where(PropertyIdentifier.scheme_id == scheme_id)
        result = await db.execute(q)
        return result.scalars().first()

    async def list_for_entity(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: str,
    ) -> List[PropertyIdentifier]:
        result = await db.execute(
            select(PropertyIdentifier)
            .where(
                and_(
                    PropertyIdentifier.entity_type == entity_type,
                    PropertyIdentifier.entity_id == str(entity_id),
                )
            )
            .order_by(PropertyIdentifier.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_filtered(
        self,
        db: AsyncSession,
        status: Optional[str] = None,
        entity_type: Optional[str] = None,
        scheme_id: Optional[str] = None,
        jurisdiction_id: Optional[str] = None,
        parcel_id: Optional[str] = None,
        building_id: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[PropertyIdentifier], int]:
        q = select(PropertyIdentifier)
        if status:
            q = q.where(PropertyIdentifier.status == status)
        if entity_type:
            q = q.where(PropertyIdentifier.entity_type == entity_type)
        if scheme_id:
            q = q.where(PropertyIdentifier.scheme_id == scheme_id)
        if jurisdiction_id:
            q = q.where(PropertyIdentifier.jurisdiction_id == jurisdiction_id)
        if parcel_id:
            q = q.where(PropertyIdentifier.parcel_id == parcel_id)
        if building_id:
            q = q.where(PropertyIdentifier.building_id == building_id)
        if search:
            q = q.where(PropertyIdentifier.identifier_value.ilike(f"%{search}%"))

        count_result = await db.execute(select(func.count()).select_from(q.subquery()))
        total = count_result.scalar_one()

        q = q.order_by(PropertyIdentifier.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(q)
        return list(result.scalars().all()), total

    async def value_exists(self, db: AsyncSession, value: str) -> bool:
        result = await db.execute(
            select(PropertyIdentifier.id).where(PropertyIdentifier.identifier_value == value)
        )
        return result.scalars().first() is not None

    async def count_by_status(self, db: AsyncSession) -> Dict[str, int]:
        result = await db.execute(
            select(PropertyIdentifier.status, func.count(PropertyIdentifier.id))
            .group_by(PropertyIdentifier.status)
        )
        return {row[0]: row[1] for row in result.all()}

    async def count_by_entity_type(self, db: AsyncSession) -> Dict[str, int]:
        result = await db.execute(
            select(PropertyIdentifier.entity_type, func.count(PropertyIdentifier.id))
            .group_by(PropertyIdentifier.entity_type)
        )
        return {row[0]: row[1] for row in result.all()}


class IdentifierLineageRepository(BaseRepository[IdentifierLineage]):
    def __init__(self):
        super().__init__(IdentifierLineage)

    async def list_for_identifier(
        self,
        db: AsyncSession,
        identifier_id: str,
    ) -> List[IdentifierLineage]:
        result = await db.execute(
            select(IdentifierLineage).where(
                or_(
                    IdentifierLineage.source_identifier_id == identifier_id,
                    IdentifierLineage.target_identifier_id == identifier_id,
                )
            ).order_by(IdentifierLineage.created_at.desc())
        )
        return list(result.scalars().all())


class IdentifierJobRepository(BaseRepository[IdentifierGenerationJob]):
    def __init__(self):
        super().__init__(IdentifierGenerationJob)

    async def list_recent(
        self, db: AsyncSession, skip: int = 0, limit: int = 20
    ) -> Tuple[List[IdentifierGenerationJob], int]:
        count_result = await db.execute(select(func.count(IdentifierGenerationJob.id)))
        total = count_result.scalar_one()
        result = await db.execute(
            select(IdentifierGenerationJob)
            .order_by(IdentifierGenerationJob.created_at.desc())
            .offset(skip).limit(limit)
        )
        return list(result.scalars().all()), total


# Singleton instances
identifier_scheme_repository = IdentifierSchemeRepository()
property_identifier_repository = PropertyIdentifierRepository()
identifier_lineage_repository = IdentifierLineageRepository()
identifier_job_repository = IdentifierJobRepository()

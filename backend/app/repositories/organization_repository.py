import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.organization import Organization
from app.models.jurisdiction import Jurisdiction
from app.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    def __init__(self):
        super().__init__(Organization)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[Organization]:
        result = await db.execute(select(Organization).where(Organization.code == code.upper().strip()))
        return result.scalars().first()

    async def get_by_name(self, db: AsyncSession, name: str) -> Optional[Organization]:
        result = await db.execute(select(Organization).where(Organization.name == name.strip()))
        return result.scalars().first()


class JurisdictionRepository(BaseRepository[Jurisdiction]):
    def __init__(self):
        super().__init__(Jurisdiction)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[Jurisdiction]:
        result = await db.execute(select(Jurisdiction).where(Jurisdiction.code == code.upper().strip()))
        return result.scalars().first()

    async def get_by_organization(self, db: AsyncSession, organization_id: uuid.UUID) -> List[Jurisdiction]:
        result = await db.execute(
            select(Jurisdiction).where(Jurisdiction.organization_id == organization_id)
        )
        return list(result.scalars().all())


organization_repository = OrganizationRepository()
jurisdiction_repository = JurisdictionRepository()

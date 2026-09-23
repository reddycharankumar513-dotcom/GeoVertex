import uuid
from typing import List, Optional, Tuple
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.property import Property
from app.models.parcel import Parcel
from app.repositories.base import BaseRepository


class PropertyRepository(BaseRepository[Property]):
    def __init__(self):
        super().__init__(Property)

    async def get_by_reference(self, db: AsyncSession, reference: str) -> Optional[Property]:
        stmt = select(Property).where(Property.property_reference == reference.strip())
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_by_parcel_id(self, db: AsyncSession, parcel_id: uuid.UUID) -> List[Property]:
        stmt = select(Property).where(Property.parcel_id == parcel_id)
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def get_with_parcel(self, db: AsyncSession, id: uuid.UUID) -> Optional[Property]:
        stmt = (
            select(Property)
            .options(
                selectinload(Property.parcel).selectinload(Parcel.jurisdiction),
            )
            .where(Property.id == id)
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    async def search_and_filter(
        self,
        db: AsyncSession,
        parcel_id: Optional[uuid.UUID] = None,
        property_type: Optional[str] = None,
        status: Optional[str] = None,
        query: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Property], int]:
        filters = []
        if parcel_id:
            filters.append(Property.parcel_id == parcel_id)
        if property_type:
            filters.append(Property.property_type == property_type.upper())
        if status:
            filters.append(Property.status == status.upper())
        if query:
            q_clean = f"%{query.strip()}%"
            filters.append(
                or_(
                    Property.property_reference.ilike(q_clean),
                    Property.address.ilike(q_clean),
                    Property.locality.ilike(q_clean),
                )
            )

        count_stmt = select(func.count(Property.id))
        if filters:
            count_stmt = count_stmt.where(*filters)
        total_res = await db.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = select(Property).order_by(Property.created_at.desc())
        if filters:
            stmt = stmt.where(*filters)
        stmt = stmt.offset(skip).limit(limit)

        items_res = await db.execute(stmt)
        items = list(items_res.scalars().all())
        return items, total


property_repository = PropertyRepository()

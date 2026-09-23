import uuid
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.floor import Floor


class FloorRepository:
    """Data access repository for Floor entities."""

    async def get_by_id(
        self,
        db: AsyncSession,
        id: uuid.UUID,
        include_units: bool = False,
    ) -> Optional[Floor]:
        stmt = select(Floor).where(Floor.id == id)
        if include_units:
            stmt = stmt.options(selectinload(Floor.units))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, db: AsyncSession, floor_code: str) -> Optional[Floor]:
        stmt = select(Floor).where(Floor.floor_code == floor_code)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_building(
        self,
        db: AsyncSession,
        building_id: uuid.UUID,
        include_units: bool = False,
    ) -> List[Floor]:
        stmt = (
            select(Floor)
            .where(Floor.building_id == building_id)
            .order_by(Floor.floor_number.asc())
        )
        if include_units:
            stmt = stmt.options(selectinload(Floor.units))
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def list(
        self,
        db: AsyncSession,
        building_id: Optional[uuid.UUID] = None,
        floor_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Floor], int]:
        stmt = select(Floor)
        count_stmt = select(func.count(Floor.id))

        if building_id:
            stmt = stmt.where(Floor.building_id == building_id)
            count_stmt = count_stmt.where(Floor.building_id == building_id)
        if floor_type:
            stmt = stmt.where(Floor.floor_type == floor_type)
            count_stmt = count_stmt.where(Floor.floor_type == floor_type)
        if status:
            stmt = stmt.where(Floor.status == status)
            count_stmt = count_stmt.where(Floor.status == status)

        stmt = stmt.order_by(Floor.floor_number.asc()).offset(skip).limit(limit)

        total_res = await db.execute(count_stmt)
        total = total_res.scalar_one()

        items_res = await db.execute(stmt)
        items = list(items_res.scalars().all())

        return items, total

    async def create(
        self,
        db: AsyncSession,
        data: Dict[str, Any],
        created_by: Optional[uuid.UUID] = None,
    ) -> Floor:
        if created_by:
            data["created_by"] = created_by
            data["updated_by"] = created_by
        floor = Floor(**data)
        db.add(floor)
        await db.commit()
        await db.refresh(floor)
        return floor

    async def update(
        self,
        db: AsyncSession,
        id: uuid.UUID,
        data: Dict[str, Any],
        updated_by: Optional[uuid.UUID] = None,
    ) -> Optional[Floor]:
        floor = await self.get_by_id(db, id)
        if not floor:
            return None
        if updated_by:
            data["updated_by"] = updated_by
        for key, val in data.items():
            if hasattr(floor, key):
                setattr(floor, key, val)
        await db.commit()
        await db.refresh(floor)
        return floor

    async def delete(self, db: AsyncSession, id: uuid.UUID) -> bool:
        floor = await self.get_by_id(db, id)
        if not floor:
            return False
        await db.delete(floor)
        await db.commit()
        return True


floor_repository = FloorRepository()

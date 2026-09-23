import uuid
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.unit import PropertyUnit


class UnitRepository:
    """Data access repository for PropertyUnit entities."""

    async def get_by_id(
        self,
        db: AsyncSession,
        id: uuid.UUID,
        include_relations: bool = False,
    ) -> Optional[PropertyUnit]:
        stmt = select(PropertyUnit).where(PropertyUnit.id == id)
        if include_relations:
            stmt = stmt.options(
                selectinload(PropertyUnit.floor),
                selectinload(PropertyUnit.building),
                selectinload(PropertyUnit.property),
            )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, db: AsyncSession, unit_code: str) -> Optional[PropertyUnit]:
        stmt = select(PropertyUnit).where(PropertyUnit.unit_code == unit_code)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_floor(
        self,
        db: AsyncSession,
        floor_id: uuid.UUID,
    ) -> List[PropertyUnit]:
        stmt = (
            select(PropertyUnit)
            .where(PropertyUnit.floor_id == floor_id)
            .order_by(PropertyUnit.unit_number.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_building(
        self,
        db: AsyncSession,
        building_id: uuid.UUID,
    ) -> List[PropertyUnit]:
        stmt = (
            select(PropertyUnit)
            .where(PropertyUnit.building_id == building_id)
            .order_by(PropertyUnit.unit_number.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def list(
        self,
        db: AsyncSession,
        floor_id: Optional[uuid.UUID] = None,
        building_id: Optional[uuid.UUID] = None,
        property_id: Optional[uuid.UUID] = None,
        unit_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[PropertyUnit], int]:
        stmt = select(PropertyUnit)
        count_stmt = select(func.count(PropertyUnit.id))

        if floor_id:
            stmt = stmt.where(PropertyUnit.floor_id == floor_id)
            count_stmt = count_stmt.where(PropertyUnit.floor_id == floor_id)
        if building_id:
            stmt = stmt.where(PropertyUnit.building_id == building_id)
            count_stmt = count_stmt.where(PropertyUnit.building_id == building_id)
        if property_id:
            stmt = stmt.where(PropertyUnit.property_id == property_id)
            count_stmt = count_stmt.where(PropertyUnit.property_id == property_id)
        if unit_type:
            stmt = stmt.where(PropertyUnit.unit_type == unit_type)
            count_stmt = count_stmt.where(PropertyUnit.unit_type == unit_type)
        if status:
            stmt = stmt.where(PropertyUnit.status == status)
            count_stmt = count_stmt.where(PropertyUnit.status == status)

        stmt = stmt.order_by(PropertyUnit.unit_code.asc()).offset(skip).limit(limit)

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
    ) -> PropertyUnit:
        if created_by:
            data["created_by"] = created_by
            data["updated_by"] = created_by
        unit = PropertyUnit(**data)
        db.add(unit)
        await db.commit()
        await db.refresh(unit)
        return unit

    async def update(
        self,
        db: AsyncSession,
        id: uuid.UUID,
        data: Dict[str, Any],
        updated_by: Optional[uuid.UUID] = None,
    ) -> Optional[PropertyUnit]:
        unit = await self.get_by_id(db, id)
        if not unit:
            return None
        if updated_by:
            data["updated_by"] = updated_by
        for key, val in data.items():
            if hasattr(unit, key):
                setattr(unit, key, val)
        await db.commit()
        await db.refresh(unit)
        return unit

    async def delete(self, db: AsyncSession, id: uuid.UUID) -> bool:
        unit = await self.get_by_id(db, id)
        if not unit:
            return False
        await db.delete(unit)
        await db.commit()
        return True


unit_repository = UnitRepository()

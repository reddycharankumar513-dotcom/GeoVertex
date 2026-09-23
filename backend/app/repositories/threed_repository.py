import uuid
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.threed import Building3DRepresentation, ThreeDAsset


class ThreeDRepository:
    """Repository handling 3D building representations and 3D asset persistence."""

    async def get_representation_by_building_id(
        self, db: AsyncSession, building_id: uuid.UUID
    ) -> Optional[Building3DRepresentation]:
        stmt = select(Building3DRepresentation).where(
            Building3DRepresentation.building_id == building_id
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_representation_by_id(
        self, db: AsyncSession, id: uuid.UUID
    ) -> Optional[Building3DRepresentation]:
        stmt = select(Building3DRepresentation).where(Building3DRepresentation.id == id)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def list_representations_by_building_ids(
        self, db: AsyncSession, building_ids: List[uuid.UUID]
    ) -> List[Building3DRepresentation]:
        if not building_ids:
            return []
        stmt = select(Building3DRepresentation).where(
            Building3DRepresentation.building_id.in_(building_ids)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def save_representation(
        self,
        db: AsyncSession,
        building_id: uuid.UUID,
        height: float,
        height_source: str = "ESTIMATED",
        height_confidence: Optional[float] = None,
        height_unit: str = "METERS",
        base_elevation: float = 0.0,
        elevation_source: str = "LOCAL_REFERENCE_PLANE",
        vertical_reference: str = "METERS_ABOVE_GROUND",
        geometry_type: str = "EXTRUSION",
        model_source: str = "EXTRUDED_FOOTPRINT",
        status: str = "ACTIVE",
        user_id: Optional[uuid.UUID] = None,
    ) -> Building3DRepresentation:
        existing = await self.get_representation_by_building_id(db, building_id)
        if existing:
            existing.height = height
            existing.height_source = height_source
            existing.height_confidence = height_confidence
            existing.height_unit = height_unit
            existing.base_elevation = base_elevation
            existing.elevation_source = elevation_source
            existing.vertical_reference = vertical_reference
            existing.geometry_type = geometry_type
            existing.model_source = model_source
            existing.status = status
            existing.updated_by = user_id
            await db.flush()
            await db.refresh(existing)
            return existing

        new_rep = Building3DRepresentation(
            building_id=building_id,
            geometry_type=geometry_type,
            height=height,
            height_source=height_source,
            height_confidence=height_confidence,
            height_unit=height_unit,
            base_elevation=base_elevation,
            elevation_source=elevation_source,
            vertical_reference=vertical_reference,
            model_source=model_source,
            status=status,
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(new_rep)
        await db.flush()
        await db.refresh(new_rep)
        return new_rep

    async def create_asset(
        self,
        db: AsyncSession,
        asset_type: str,
        storage_location: str,
        format: str = "JSON_EXTRUSION",
        building_id: Optional[uuid.UUID] = None,
        representation_id: Optional[uuid.UUID] = None,
        source: str = "SYSTEM_GENERATED",
        status: str = "ACTIVE",
        metadata_json: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> ThreeDAsset:
        asset = ThreeDAsset(
            building_id=building_id,
            representation_id=representation_id,
            asset_type=asset_type,
            storage_location=storage_location,
            format=format,
            source=source,
            status=status,
            metadata_json=metadata_json,
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(asset)
        await db.flush()
        await db.refresh(asset)
        return asset

    async def list_assets(
        self,
        db: AsyncSession,
        building_id: Optional[uuid.UUID] = None,
        asset_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[ThreeDAsset], int]:
        stmt = select(ThreeDAsset)
        count_stmt = select(func.count(ThreeDAsset.id))

        if building_id:
            stmt = stmt.where(ThreeDAsset.building_id == building_id)
            count_stmt = count_stmt.where(ThreeDAsset.building_id == building_id)
        if asset_type:
            stmt = stmt.where(ThreeDAsset.asset_type == asset_type.upper())
            count_stmt = count_stmt.where(ThreeDAsset.asset_type == asset_type.upper())
        if status:
            stmt = stmt.where(ThreeDAsset.status == status.upper())
            count_stmt = count_stmt.where(ThreeDAsset.status == status.upper())

        stmt = stmt.order_by(ThreeDAsset.created_at.desc()).offset(skip).limit(limit)
        items_res = await db.execute(stmt)
        count_res = await db.execute(count_stmt)

        return list(items_res.scalars().all()), int(count_res.scalar() or 0)

    async def get_asset_by_id(self, db: AsyncSession, id: uuid.UUID) -> Optional[ThreeDAsset]:
        stmt = select(ThreeDAsset).where(ThreeDAsset.id == id)
        res = await db.execute(stmt)
        return res.scalars().first()

    async def delete_asset_by_id(self, db: AsyncSession, id: uuid.UUID) -> bool:
        asset = await self.get_asset_by_id(db, id)
        if not asset:
            return False
        await db.delete(asset)
        await db.flush()
        return True


threed_repository = ThreeDRepository()

import uuid
from typing import List, Optional, Tuple
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.gis.geometry import GeometryEngine
from app.models.building import BuildingFootprint
from app.models.parcel import Parcel
from app.repositories.base import BaseRepository
import shapely


class BuildingRepository(BaseRepository[BuildingFootprint]):
    def __init__(self):
        super().__init__(BuildingFootprint)

    async def get_by_reference(self, db: AsyncSession, reference: str) -> Optional[BuildingFootprint]:
        stmt = select(BuildingFootprint).where(BuildingFootprint.building_reference == reference.strip())
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_by_parcel_id(self, db: AsyncSession, parcel_id: uuid.UUID) -> List[BuildingFootprint]:
        stmt = select(BuildingFootprint).where(BuildingFootprint.parcel_id == parcel_id)
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def get_with_parcel(self, db: AsyncSession, id: uuid.UUID) -> Optional[BuildingFootprint]:
        stmt = (
            select(BuildingFootprint)
            .options(selectinload(BuildingFootprint.parcel))
            .where(BuildingFootprint.id == id)
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    async def search_and_filter(
        self,
        db: AsyncSession,
        parcel_id: Optional[uuid.UUID] = None,
        building_type: Optional[str] = None,
        status: Optional[str] = None,
        query: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[BuildingFootprint], int]:
        filters = []
        if parcel_id:
            filters.append(BuildingFootprint.parcel_id == parcel_id)
        if building_type:
            filters.append(BuildingFootprint.building_type == building_type.upper())
        if status:
            filters.append(BuildingFootprint.status == status.upper())
        if query:
            q_clean = f"%{query.strip()}%"
            filters.append(BuildingFootprint.building_reference.ilike(q_clean))

        count_stmt = select(func.count(BuildingFootprint.id))
        if filters:
            count_stmt = count_stmt.where(*filters)
        total_res = await db.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = select(BuildingFootprint).order_by(BuildingFootprint.created_at.desc())
        if filters:
            stmt = stmt.where(*filters)
        stmt = stmt.offset(skip).limit(limit)

        items_res = await db.execute(stmt)
        items = list(items_res.scalars().all())
        return items, total

    async def list(
        self,
        db: AsyncSession,
        parcel_id: Optional[uuid.UUID] = None,
        building_type: Optional[str] = None,
        status: Optional[str] = None,
        query: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[BuildingFootprint], int]:
        return await self.search_and_filter(
            db=db,
            parcel_id=parcel_id,
            building_type=building_type,
            status=status,
            query=query,
            skip=skip,
            limit=limit,
        )

    async def get_by_bbox(
        self,
        db: AsyncSession,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        parcel_id: Optional[uuid.UUID] = None,
        limit: int = 500,
    ) -> List[BuildingFootprint]:
        filters = []
        if parcel_id:
            filters.append(BuildingFootprint.parcel_id == parcel_id)

        stmt = select(BuildingFootprint)
        if filters:
            stmt = stmt.where(*filters)
        stmt = stmt.limit(limit * 2)

        res = await db.execute(stmt)
        all_candidates = list(res.scalars().all())

        bbox_poly = shapely.geometry.box(min_lon, min_lat, max_lon, max_lat)
        matched = []
        for b in all_candidates:
            if not b.geometry_wkt:
                continue
            try:
                geom = GeometryEngine.parse_geometry(b.geometry_wkt)
                if geom.intersects(bbox_poly):
                    matched.append(b)
                    if len(matched) >= limit:
                        break
            except Exception:
                continue

        return matched

    async def identify_at_point(
        self,
        db: AsyncSession,
        lon: float,
        lat: float,
        radius_meters: float = 30.0,
    ) -> List[Tuple[BuildingFootprint, float]]:
        point = shapely.geometry.Point(lon, lat)
        stmt = select(BuildingFootprint)
        res = await db.execute(stmt)
        candidates = list(res.scalars().all())

        results = []
        for b in candidates:
            if not b.geometry_wkt:
                continue
            try:
                geom = GeometryEngine.parse_geometry(b.geometry_wkt)
                if geom.contains(point):
                    results.append((b, 0.0))
                else:
                    dist_deg = geom.distance(point)
                    meters_per_deg = 111320.0
                    dist_m = dist_deg * meters_per_deg
                    if dist_m <= radius_meters:
                        results.append((b, round(dist_m, 2)))
            except Exception:
                continue

        results.sort(key=lambda x: x[1])
        return results


building_repository = BuildingRepository()

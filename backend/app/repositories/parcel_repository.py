import uuid
from typing import List, Optional, Tuple
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.gis.geometry import GeometryEngine
from app.models.parcel import Parcel
from app.models.jurisdiction import Jurisdiction
from app.repositories.base import BaseRepository
import shapely


class ParcelRepository(BaseRepository[Parcel]):
    def __init__(self):
        super().__init__(Parcel)

    async def get_by_id_with_relations(self, db: AsyncSession, id: uuid.UUID) -> Optional[Parcel]:
        stmt = (
            select(Parcel)
            .options(
                selectinload(Parcel.jurisdiction),
                selectinload(Parcel.properties),
                selectinload(Parcel.buildings),
            )
            .where(Parcel.id == id)
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_by_code(self, db: AsyncSession, parcel_code: str) -> Optional[Parcel]:
        stmt = select(Parcel).where(Parcel.parcel_code == parcel_code.strip())
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_by_number_and_jurisdiction(
        self, db: AsyncSession, jurisdiction_id: uuid.UUID, parcel_number: str
    ) -> Optional[Parcel]:
        stmt = select(Parcel).where(
            Parcel.jurisdiction_id == jurisdiction_id,
            Parcel.parcel_number == parcel_number.strip(),
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def search_and_filter(
        self,
        db: AsyncSession,
        jurisdiction_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        land_use: Optional[str] = None,
        query: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Parcel], int]:
        filters = []
        if jurisdiction_id:
            filters.append(Parcel.jurisdiction_id == jurisdiction_id)
        if status:
            filters.append(Parcel.status == status.upper())
        if land_use:
            filters.append(Parcel.land_use == land_use.upper())
        if query:
            q_clean = f"%{query.strip()}%"
            filters.append(
                or_(
                    Parcel.parcel_number.ilike(q_clean),
                    Parcel.parcel_code.ilike(q_clean),
                    Parcel.survey_number.ilike(q_clean),
                )
            )

        # Count total
        count_stmt = select(func.count(Parcel.id))
        if filters:
            count_stmt = count_stmt.where(*filters)
        total_res = await db.execute(count_stmt)
        total = total_res.scalar_one()

        # Query items
        stmt = select(Parcel).order_by(Parcel.created_at.desc())
        if filters:
            stmt = stmt.where(*filters)
        stmt = stmt.offset(skip).limit(limit)

        items_res = await db.execute(stmt)
        items = list(items_res.scalars().all())
        return items, total

    async def get_by_bbox(
        self,
        db: AsyncSession,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        jurisdiction_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        limit: int = 500,
    ) -> List[Parcel]:
        """Spatial bounding box query. Performs envelope check in Python/Shapely or database."""
        filters = []
        if jurisdiction_id:
            filters.append(Parcel.jurisdiction_id == jurisdiction_id)
        if status:
            filters.append(Parcel.status == status.upper())

        stmt = select(Parcel)
        if filters:
            stmt = stmt.where(*filters)
        stmt = stmt.limit(limit * 2)

        res = await db.execute(stmt)
        all_candidates = list(res.scalars().all())

        # Spatial filter with bbox polygon
        bbox_poly = shapely.geometry.box(min_lon, min_lat, max_lon, max_lat)
        matched = []
        for p in all_candidates:
            if not p.geometry_wkt:
                continue
            try:
                geom = GeometryEngine.parse_geometry(p.geometry_wkt)
                if geom.intersects(bbox_poly):
                    matched.append(p)
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
        radius_meters: float = 50.0,
    ) -> List[Tuple[Parcel, float]]:
        """Identifies parcels containing or within radius of a point.
        Returns list of (Parcel, distance_in_meters).
        """
        point = shapely.geometry.Point(lon, lat)
        stmt = select(Parcel).where(Parcel.status == "ACTIVE")
        res = await db.execute(stmt)
        candidates = list(res.scalars().all())

        results = []
        for p in candidates:
            if not p.geometry_wkt:
                continue
            try:
                geom = GeometryEngine.parse_geometry(p.geometry_wkt)
                if geom.contains(point):
                    results.append((p, 0.0))
                else:
                    dist_deg = geom.distance(point)
                    # Approximate degree to meters conversion around this latitude
                    meters_per_deg = 111320.0
                    dist_m = dist_deg * meters_per_deg
                    if dist_m <= radius_meters:
                        results.append((p, round(dist_m, 2)))
            except Exception:
                continue

        results.sort(key=lambda x: x[1])
        return results


parcel_repository = ParcelRepository()

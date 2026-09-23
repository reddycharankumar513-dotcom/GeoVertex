import uuid
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import BadRequestException, ConflictException, NotFoundException
from app.gis.geometry import GeometryEngine
from app.models.building import BuildingFootprint
from app.repositories.audit_repository import audit_repository
from app.repositories.building_repository import building_repository
from app.repositories.parcel_repository import parcel_repository
from app.schemas.building import BuildingCreate, BuildingUpdate
from app.services.spatial_validation_service import spatial_validation_service


class BuildingService:
    """Service layer managing BuildingFootprint lifecycle, spatial relationships, and validation."""

    async def create_building(
        self,
        db: AsyncSession,
        data: BuildingCreate,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> BuildingFootprint:
        # Check unique reference
        existing = await building_repository.get_by_reference(db, data.building_reference)
        if existing:
            raise ConflictException(f"Building with reference '{data.building_reference}' already exists")

        # Verify parcel if provided
        if data.parcel_id:
            parcel = await parcel_repository.get_by_id(db, data.parcel_id)
            if not parcel:
                raise NotFoundException(f"Associated parcel with ID '{data.parcel_id}' does not exist")

        # Validate geometry
        validation = await spatial_validation_service.validate_building_candidate(
            db=db,
            geometry_input=data.geometry,
            parcel_id=data.parcel_id,
            source_srid=data.source_srid,
        )
        if not validation.valid:
            raise BadRequestException(
                message=validation.errors[0].message if validation.errors else "Building geometry validation failed",
                details={"valid": False, "errors": [e.model_dump() for e in validation.errors]},
            )

        parsed_geom = GeometryEngine.parse_geometry(data.geometry, source_srid=data.source_srid)
        area_m2 = GeometryEngine.calculate_geodesic_area(parsed_geom)
        geom_wkt = GeometryEngine.to_wkt(parsed_geom)

        building = BuildingFootprint(
            parcel_id=data.parcel_id,
            building_reference=data.building_reference.strip(),
            building_type=data.building_type.upper(),
            status=data.status.upper(),
            area=area_m2,
            height_estimate=data.height_estimate,
            geometry=geom_wkt,
            geometry_wkt=geom_wkt,
            source=data.source,
            source_reference=data.source_reference,
            created_by=actor_id,
            updated_by=actor_id,
        )
        created = await building_repository.create(db, building)

        await audit_repository.log_event(
            db=db,
            action="BUILDING_CREATED",
            entity_type="BUILDING",
            entity_id=str(created.id),
            actor_user_id=actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "building_reference": created.building_reference,
                "parcel_id": str(created.parcel_id) if created.parcel_id else None,
                "area_sq_m": created.area,
                "height_estimate": created.height_estimate,
            },
        )
        return created

    async def get_building(self, db: AsyncSession, id: uuid.UUID) -> BuildingFootprint:
        building = await building_repository.get_with_parcel(db, id)
        if not building:
            raise NotFoundException(f"Building with ID '{id}' not found")
        return building

    async def update_building(
        self,
        db: AsyncSession,
        id: uuid.UUID,
        data: BuildingUpdate,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> BuildingFootprint:
        building = await building_repository.get_by_id(db, id)
        if not building:
            raise NotFoundException(f"Building with ID '{id}' not found")

        old_details: Dict[str, Any] = {
            "building_reference": building.building_reference,
            "status": building.status,
            "area": building.area,
        }

        if data.building_reference and data.building_reference.strip() != building.building_reference:
            existing = await building_repository.get_by_reference(db, data.building_reference)
            if existing and existing.id != id:
                raise ConflictException(f"Building with reference '{data.building_reference}' already exists")
            building.building_reference = data.building_reference.strip()

        if data.parcel_id is not None:
            if data.parcel_id:
                parcel = await parcel_repository.get_by_id(db, data.parcel_id)
                if not parcel:
                    raise NotFoundException(f"Associated parcel with ID '{data.parcel_id}' does not exist")
            building.parcel_id = data.parcel_id

        if data.building_type:
            building.building_type = data.building_type.upper()
        if data.status:
            building.status = data.status.upper()
        if data.height_estimate is not None:
            building.height_estimate = data.height_estimate
        if data.source_reference is not None:
            building.source_reference = data.source_reference

        if data.geometry is not None:
            source_srid = data.source_srid or 4326
            validation = await spatial_validation_service.validate_building_candidate(
                db=db,
                geometry_input=data.geometry,
                parcel_id=building.parcel_id,
                source_srid=source_srid,
            )
            if not validation.valid:
                raise BadRequestException(
                    message=validation.errors[0].message if validation.errors else "Updated geometry is invalid",
                    details={"valid": False, "errors": [e.model_dump() for e in validation.errors]},
                )

            parsed_geom = GeometryEngine.parse_geometry(data.geometry, source_srid=source_srid)
            building.area = GeometryEngine.calculate_geodesic_area(parsed_geom)
            geom_wkt = GeometryEngine.to_wkt(parsed_geom)
            building.geometry = geom_wkt
            building.geometry_wkt = geom_wkt

        building.updated_by = actor_id
        await db.flush()
        await db.refresh(building)

        await audit_repository.log_event(
            db=db,
            action="BUILDING_UPDATED",
            entity_type="BUILDING",
            entity_id=str(building.id),
            actor_user_id=actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "old": old_details,
                "new": {"building_reference": building.building_reference, "area": building.area},
            },
        )
        return building

    async def delete_building(
        self,
        db: AsyncSession,
        id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        building = await building_repository.get_by_id(db, id)
        if not building:
            raise NotFoundException(f"Building with ID '{id}' not found")

        ref = building.building_reference
        success = await building_repository.delete_by_id(db, id)
        if success:
            await audit_repository.log_event(
                db=db,
                action="BUILDING_DELETED",
                entity_type="BUILDING",
                entity_id=str(id),
                actor_user_id=actor_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"building_reference": ref},
            )
        return success

    async def list_buildings(
        self,
        db: AsyncSession,
        parcel_id: Optional[uuid.UUID] = None,
        building_type: Optional[str] = None,
        status: Optional[str] = None,
        query: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[BuildingFootprint], int]:
        return await building_repository.search_and_filter(
            db=db,
            parcel_id=parcel_id,
            building_type=building_type,
            status=status,
            query=query,
            skip=skip,
            limit=limit,
        )

    async def get_buildings_in_bbox(
        self,
        db: AsyncSession,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        parcel_id: Optional[uuid.UUID] = None,
        limit: int = 500,
    ) -> List[BuildingFootprint]:
        return await building_repository.get_by_bbox(
            db=db,
            min_lon=min_lon,
            min_lat=min_lat,
            max_lon=max_lon,
            max_lat=max_lat,
            parcel_id=parcel_id,
            limit=limit,
        )


building_service = BuildingService()

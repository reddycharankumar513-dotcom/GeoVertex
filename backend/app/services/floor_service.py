import uuid
from typing import Any, Dict, List, Optional, Tuple
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import BadRequestException, ConflictException, NotFoundException
from app.gis.geometry import GeometryEngine
from app.models.user import User
from app.repositories.audit_repository import audit_repository
from app.repositories.building_repository import building_repository
from app.repositories.floor_repository import floor_repository
from app.repositories.parcel_repository import parcel_repository
from app.schemas.floor import FloorCreate, FloorDetailResponse, FloorResponse, FloorUpdate
from app.services.spatial_validation_service import spatial_validation_service


class FloorService:
    """Domain service managing building floor slabs, vertical stacking, and spatial lifecycle."""

    async def list_floors(
        self,
        db: AsyncSession,
        building_id: Optional[uuid.UUID] = None,
        floor_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[FloorDetailResponse], int]:
        floors, total = await floor_repository.list(
            db=db,
            building_id=building_id,
            floor_type=floor_type,
            status=status,
            skip=skip,
            limit=limit,
        )

        responses = []
        for f in floors:
            bldg = await building_repository.get_by_id(db, f.building_id)
            parcel_code = None
            if bldg and bldg.parcel_id:
                p = await parcel_repository.get_by_id(db, bldg.parcel_id)
                parcel_code = p.parcel_code if p else None

            responses.append(
                FloorDetailResponse(
                    id=f.id,
                    building_id=f.building_id,
                    floor_number=f.floor_number,
                    floor_code=f.floor_code,
                    floor_name=f.floor_name,
                    floor_type=f.floor_type,
                    elevation_min_m=f.elevation_min_m,
                    elevation_max_m=f.elevation_max_m,
                    height_m=f.height_m,
                    area_sqm=f.area_sqm,
                    confidence=f.confidence,
                    status=f.status,
                    source=f.source,
                    geometry_wkt=f.geometry_wkt,
                    created_at=f.created_at,
                    updated_at=f.updated_at,
                    building_reference=bldg.building_reference if bldg else None,
                    parcel_code=parcel_code,
                    units_count=len(f.units) if hasattr(f, "units") and f.units else 0,
                )
            )
        return responses, total

    async def get_floor(self, db: AsyncSession, id: uuid.UUID) -> FloorDetailResponse:
        floor = await floor_repository.get_by_id(db, id, include_units=True)
        if not floor:
            raise NotFoundException(f"Floor with ID '{id}' was not found")

        bldg = await building_repository.get_by_id(db, floor.building_id)
        parcel_code = None
        if bldg and bldg.parcel_id:
            p = await parcel_repository.get_by_id(db, bldg.parcel_id)
            parcel_code = p.parcel_code if p else None

        return FloorDetailResponse(
            id=floor.id,
            building_id=floor.building_id,
            floor_number=floor.floor_number,
            floor_code=floor.floor_code,
            floor_name=floor.floor_name,
            floor_type=floor.floor_type,
            elevation_min_m=floor.elevation_min_m,
            elevation_max_m=floor.elevation_max_m,
            height_m=floor.height_m,
            area_sqm=floor.area_sqm,
            confidence=floor.confidence,
            status=floor.status,
            source=floor.source,
            geometry_wkt=floor.geometry_wkt,
            created_at=floor.created_at,
            updated_at=floor.updated_at,
            building_reference=bldg.building_reference if bldg else None,
            parcel_code=parcel_code,
            units_count=len(floor.units) if floor.units else 0,
        )

    async def get_building_floors(self, db: AsyncSession, building_id: uuid.UUID) -> List[FloorDetailResponse]:
        bldg = await building_repository.get_by_id(db, building_id)
        if not bldg:
            raise NotFoundException(f"Building with ID '{building_id}' was not found")

        floors = await floor_repository.get_by_building(db, building_id, include_units=True)
        parcel_code = None
        if bldg.parcel_id:
            p = await parcel_repository.get_by_id(db, bldg.parcel_id)
            parcel_code = p.parcel_code if p else None

        return [
            FloorDetailResponse(
                id=f.id,
                building_id=f.building_id,
                floor_number=f.floor_number,
                floor_code=f.floor_code,
                floor_name=f.floor_name,
                floor_type=f.floor_type,
                elevation_min_m=f.elevation_min_m,
                elevation_max_m=f.elevation_max_m,
                height_m=f.height_m,
                area_sqm=f.area_sqm,
                confidence=f.confidence,
                status=f.status,
                source=f.source,
                geometry_wkt=f.geometry_wkt,
                created_at=f.created_at,
                updated_at=f.updated_at,
                building_reference=bldg.building_reference,
                parcel_code=parcel_code,
                units_count=len(f.units) if f.units else 0,
            )
            for f in floors
        ]

    async def create_floor(
        self,
        db: AsyncSession,
        data: FloorCreate,
        current_user: User,
        request: Optional[Request] = None,
    ) -> FloorDetailResponse:
        # 1. Verify parent building
        bldg = await building_repository.get_by_id(db, data.building_id)
        if not bldg:
            raise NotFoundException(f"Building with ID '{data.building_id}' not found")

        # 2. Inherit building footprint if floor geometry omitted
        geometry_input = data.geometry if data.geometry is not None else bldg.geometry_wkt
        if not geometry_input:
            raise BadRequestException("Parent building does not have a footprint geometry to inherit")

        # 3. Spatial & vertical stacking validation
        val_res = await spatial_validation_service.validate_floor_candidate(
            db=db,
            building_id=data.building_id,
            floor_number=data.floor_number,
            elevation_min_m=data.elevation_min_m,
            elevation_max_m=data.elevation_max_m,
            geometry_input=geometry_input,
            source_srid=data.source_srid,
        )
        if not val_res.valid:
            error_details = [{"code": e.code, "message": e.message} for e in val_res.errors]
            raise BadRequestException("Floor validation failed", details={"errors": error_details})

        # 4. Check unique code
        existing = await floor_repository.get_by_code(db, data.floor_code)
        if existing:
            raise ConflictException(f"Floor with code '{data.floor_code}' already exists")

        # 5. Compute area and WKT
        parsed_geom = GeometryEngine.parse_geometry(geometry_input, source_srid=data.source_srid)
        area_m2 = GeometryEngine.calculate_geodesic_area(parsed_geom)
        wkt_str = GeometryEngine.to_wkt(parsed_geom)
        height = round(data.elevation_max_m - data.elevation_min_m, 2)

        floor_data = {
            "building_id": data.building_id,
            "floor_number": data.floor_number,
            "floor_code": data.floor_code,
            "floor_name": data.floor_name,
            "floor_type": data.floor_type,
            "elevation_min_m": data.elevation_min_m,
            "elevation_max_m": data.elevation_max_m,
            "height_m": height,
            "area_sqm": area_m2,
            "geometry": wkt_str,
            "geometry_wkt": wkt_str,
            "confidence": data.confidence,
            "status": data.status,
            "source": data.source,
        }

        floor = await floor_repository.create(db, floor_data, created_by=current_user.id)

        # 6. Audit event
        await audit_repository.log_event(
            db=db,
            actor_user_id=current_user.id,
            action="FLOOR_CREATED",
            entity_type="FLOOR",
            entity_id=str(floor.id),
            details={
                "floor_code": floor.floor_code,
                "floor_number": floor.floor_number,
                "elevation_range": [floor.elevation_min_m, floor.elevation_max_m],
                "area_sqm": floor.area_sqm,
            },
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )

        return await self.get_floor(db, floor.id)

    async def update_floor(
        self,
        db: AsyncSession,
        id: uuid.UUID,
        data: FloorUpdate,
        current_user: User,
        request: Optional[Request] = None,
    ) -> FloorDetailResponse:
        floor = await floor_repository.get_by_id(db, id)
        if not floor:
            raise NotFoundException(f"Floor with ID '{id}' was not found")

        old_values = {
            "floor_code": floor.floor_code,
            "floor_number": floor.floor_number,
            "elevation_min_m": floor.elevation_min_m,
            "elevation_max_m": floor.elevation_max_m,
            "height_m": floor.height_m,
            "status": floor.status,
        }

        update_dict = data.model_dump(exclude_unset=True)

        target_floor_number = data.floor_number if data.floor_number is not None else floor.floor_number
        target_elev_min = data.elevation_min_m if data.elevation_min_m is not None else floor.elevation_min_m
        target_elev_max = data.elevation_max_m if data.elevation_max_m is not None else floor.elevation_max_m
        geometry_input = data.geometry if data.geometry is not None else floor.geometry_wkt

        # Validate modifications
        val_res = await spatial_validation_service.validate_floor_candidate(
            db=db,
            building_id=floor.building_id,
            floor_number=target_floor_number,
            elevation_min_m=target_elev_min,
            elevation_max_m=target_elev_max,
            geometry_input=geometry_input,
            current_floor_id=floor.id,
            source_srid=data.source_srid or 4326,
        )
        if not val_res.valid:
            error_details = [{"code": e.code, "message": e.message} for e in val_res.errors]
            raise BadRequestException("Floor validation failed", details={"errors": error_details})

        if "geometry" in update_dict and data.geometry is not None:
            parsed = GeometryEngine.parse_geometry(data.geometry, source_srid=data.source_srid or 4326)
            update_dict["geometry"] = GeometryEngine.to_wkt(parsed)
            update_dict["geometry_wkt"] = update_dict["geometry"]
            update_dict["area_sqm"] = GeometryEngine.calculate_geodesic_area(parsed)

        if "elevation_min_m" in update_dict or "elevation_max_m" in update_dict:
            update_dict["height_m"] = round(target_elev_max - target_elev_min, 2)

        updated_floor = await floor_repository.update(db, id, update_dict, updated_by=current_user.id)

        # Audit event
        await audit_repository.log_event(
            db=db,
            actor_user_id=current_user.id,
            action="FLOOR_UPDATED",
            entity_type="FLOOR",
            entity_id=str(floor.id),
            details={"old": old_values, "new": update_dict},
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )

        return await self.get_floor(db, id)

    async def delete_floor(
        self,
        db: AsyncSession,
        id: uuid.UUID,
        current_user: User,
        request: Optional[Request] = None,
    ) -> bool:
        floor = await floor_repository.get_by_id(db, id)
        if not floor:
            raise NotFoundException(f"Floor with ID '{id}' was not found")

        # Audit
        await audit_repository.log_event(
            db=db,
            actor_user_id=current_user.id,
            action="FLOOR_DELETED",
            entity_type="FLOOR",
            entity_id=str(id),
            details={"floor_code": floor.floor_code, "building_id": str(floor.building_id)},
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )
        await floor_repository.delete(db, id)
        return True


floor_service = FloorService()

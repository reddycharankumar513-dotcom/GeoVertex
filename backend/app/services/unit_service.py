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
from app.repositories.property_repository import property_repository
from app.repositories.unit_repository import unit_repository
from app.schemas.unit import UnitCreate, UnitDetailResponse, UnitResponse, UnitUpdate
from app.services.spatial_validation_service import spatial_validation_service


class UnitService:
    """Domain service managing property units, spatial floor subdivisions, and property attachments."""

    async def list_units(
        self,
        db: AsyncSession,
        floor_id: Optional[uuid.UUID] = None,
        building_id: Optional[uuid.UUID] = None,
        property_id: Optional[uuid.UUID] = None,
        unit_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[UnitDetailResponse], int]:
        units, total = await unit_repository.list(
            db=db,
            floor_id=floor_id,
            building_id=building_id,
            property_id=property_id,
            unit_type=unit_type,
            status=status,
            skip=skip,
            limit=limit,
        )

        responses = []
        for u in units:
            responses.append(await self._build_detail_response(db, u))
        return responses, total

    async def get_unit(self, db: AsyncSession, id: uuid.UUID) -> UnitDetailResponse:
        unit = await unit_repository.get_by_id(db, id, include_relations=True)
        if not unit:
            raise NotFoundException(f"Unit with ID '{id}' was not found")
        return await self._build_detail_response(db, unit)

    async def get_floor_units(self, db: AsyncSession, floor_id: uuid.UUID) -> List[UnitDetailResponse]:
        floor = await floor_repository.get_by_id(db, floor_id)
        if not floor:
            raise NotFoundException(f"Floor with ID '{floor_id}' was not found")

        units = await unit_repository.get_by_floor(db, floor_id)
        return [await self._build_detail_response(db, u) for u in units]

    async def create_unit(
        self,
        db: AsyncSession,
        data: UnitCreate,
        current_user: User,
        request: Optional[Request] = None,
    ) -> UnitDetailResponse:
        # 1. Verify parent floor
        floor = await floor_repository.get_by_id(db, data.floor_id)
        if not floor:
            raise NotFoundException(f"Parent floor with ID '{data.floor_id}' was not found")

        # 2. Check property if specified
        if data.property_id:
            prop = await property_repository.get_by_id(db, data.property_id)
            if not prop:
                raise NotFoundException(f"Property record with ID '{data.property_id}' was not found")

        # 3. Spatial & elevation validation
        val_res = await spatial_validation_service.validate_unit_candidate(
            db=db,
            floor_id=data.floor_id,
            unit_number=data.unit_number,
            elevation_min_m=data.elevation_min_m,
            elevation_max_m=data.elevation_max_m,
            geometry_input=data.geometry,
            source_srid=data.source_srid,
        )
        if not val_res.valid:
            error_details = [{"code": e.code, "message": e.message} for e in val_res.errors]
            raise BadRequestException("Unit validation failed", details={"errors": error_details})

        # 4. Check unique code
        existing = await unit_repository.get_by_code(db, data.unit_code)
        if existing:
            raise ConflictException(f"Unit with code '{data.unit_code}' already exists")

        # 5. Compute area and WKT
        parsed_geom = GeometryEngine.parse_geometry(data.geometry, source_srid=data.source_srid)
        gross_area = GeometryEngine.calculate_geodesic_area(parsed_geom)
        net_area = data.net_area_sqm if data.net_area_sqm > 0 else round(gross_area * 0.85, 2)
        wkt_str = GeometryEngine.to_wkt(parsed_geom)
        height = round(data.elevation_max_m - data.elevation_min_m, 2)

        unit_data = {
            "floor_id": data.floor_id,
            "building_id": floor.building_id,  # ensure strictly matching parent floor's building
            "property_id": data.property_id,
            "unit_number": data.unit_number,
            "unit_code": data.unit_code,
            "unit_type": data.unit_type,
            "gross_area_sqm": gross_area,
            "net_area_sqm": net_area,
            "elevation_min_m": data.elevation_min_m,
            "elevation_max_m": data.elevation_max_m,
            "height_m": height,
            "geometry": wkt_str,
            "geometry_wkt": wkt_str,
            "status": data.status,
            "ownership_status": data.ownership_status,
        }

        unit = await unit_repository.create(db, unit_data, created_by=current_user.id)

        # 6. Audit event
        await audit_repository.log_event(
            db=db,
            actor_user_id=current_user.id,
            action="UNIT_CREATED",
            entity_type="UNIT",
            entity_id=str(unit.id),
            details={
                "unit_code": unit.unit_code,
                "unit_number": unit.unit_number,
                "floor_id": str(unit.floor_id),
                "gross_area_sqm": unit.gross_area_sqm,
                "elevation_range": [unit.elevation_min_m, unit.elevation_max_m],
            },
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )

        return await self.get_unit(db, unit.id)

    async def update_unit(
        self,
        db: AsyncSession,
        id: uuid.UUID,
        data: UnitUpdate,
        current_user: User,
        request: Optional[Request] = None,
    ) -> UnitDetailResponse:
        unit = await unit_repository.get_by_id(db, id)
        if not unit:
            raise NotFoundException(f"Unit with ID '{id}' was not found")

        old_values = {
            "unit_code": unit.unit_code,
            "unit_number": unit.unit_number,
            "elevation_min_m": unit.elevation_min_m,
            "elevation_max_m": unit.elevation_max_m,
            "status": unit.status,
        }

        update_dict = data.model_dump(exclude_unset=True)

        target_number = data.unit_number if data.unit_number is not None else unit.unit_number
        target_elev_min = data.elevation_min_m if data.elevation_min_m is not None else unit.elevation_min_m
        target_elev_max = data.elevation_max_m if data.elevation_max_m is not None else unit.elevation_max_m
        geometry_input = data.geometry if data.geometry is not None else unit.geometry_wkt

        val_res = await spatial_validation_service.validate_unit_candidate(
            db=db,
            floor_id=unit.floor_id,
            unit_number=target_number,
            elevation_min_m=target_elev_min,
            elevation_max_m=target_elev_max,
            geometry_input=geometry_input,
            current_unit_id=unit.id,
            source_srid=data.source_srid or 4326,
        )
        if not val_res.valid:
            error_details = [{"code": e.code, "message": e.message} for e in val_res.errors]
            raise BadRequestException("Unit validation failed", details={"errors": error_details})

        if "geometry" in update_dict and data.geometry is not None:
            parsed = GeometryEngine.parse_geometry(data.geometry, source_srid=data.source_srid or 4326)
            update_dict["geometry"] = GeometryEngine.to_wkt(parsed)
            update_dict["geometry_wkt"] = update_dict["geometry"]
            update_dict["gross_area_sqm"] = GeometryEngine.calculate_geodesic_area(parsed)

        if "elevation_min_m" in update_dict or "elevation_max_m" in update_dict:
            update_dict["height_m"] = round(target_elev_max - target_elev_min, 2)

        updated_unit = await unit_repository.update(db, id, update_dict, updated_by=current_user.id)

        # Audit event
        await audit_repository.log_event(
            db=db,
            actor_user_id=current_user.id,
            action="UNIT_UPDATED",
            entity_type="UNIT",
            entity_id=str(unit.id),
            details={"old": old_values, "new": update_dict},
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )

        return await self.get_unit(db, id)

    async def delete_unit(
        self,
        db: AsyncSession,
        id: uuid.UUID,
        current_user: User,
        request: Optional[Request] = None,
    ) -> bool:
        unit = await unit_repository.get_by_id(db, id)
        if not unit:
            raise NotFoundException(f"Unit with ID '{id}' was not found")

        # Audit
        await audit_repository.log_event(
            db=db,
            actor_user_id=current_user.id,
            action="UNIT_DELETED",
            entity_type="UNIT",
            entity_id=str(id),
            details={"unit_code": unit.unit_code, "floor_id": str(unit.floor_id)},
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )
        await unit_repository.delete(db, id)
        return True

    async def _build_detail_response(self, db: AsyncSession, unit: Any) -> UnitDetailResponse:
        floor = await floor_repository.get_by_id(db, unit.floor_id)
        bldg = await building_repository.get_by_id(db, unit.building_id) if unit.building_id else None
        prop = await property_repository.get_by_id(db, unit.property_id) if unit.property_id else None

        parcel_code = None
        if bldg and bldg.parcel_id:
            p = await parcel_repository.get_by_id(db, bldg.parcel_id)
            parcel_code = p.parcel_code if p else None

        return UnitDetailResponse(
            id=unit.id,
            floor_id=unit.floor_id,
            building_id=unit.building_id,
            property_id=unit.property_id,
            unit_number=unit.unit_number,
            unit_code=unit.unit_code,
            unit_type=unit.unit_type,
            gross_area_sqm=unit.gross_area_sqm,
            net_area_sqm=unit.net_area_sqm,
            elevation_min_m=unit.elevation_min_m,
            elevation_max_m=unit.elevation_max_m,
            height_m=unit.height_m,
            geometry_wkt=unit.geometry_wkt,
            status=unit.status,
            ownership_status=unit.ownership_status,
            created_at=unit.created_at,
            updated_at=unit.updated_at,
            floor_code=floor.floor_code if floor else None,
            floor_number=floor.floor_number if floor else None,
            building_reference=bldg.building_reference if bldg else None,
            property_reference=prop.property_reference if prop else None,
            parcel_code=parcel_code,
        )


unit_service = UnitService()

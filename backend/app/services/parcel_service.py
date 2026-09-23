import uuid
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import BadRequestException, ConflictException, NotFoundException
from app.gis.geometry import GeometryEngine
from app.models.parcel import Parcel
from app.models.jurisdiction import Jurisdiction
from app.repositories.audit_repository import audit_repository
from app.repositories.jurisdiction_repository import jurisdiction_repository
from app.repositories.parcel_repository import parcel_repository
from app.schemas.parcel import ParcelCreate, ParcelUpdate
from app.services.spatial_validation_service import spatial_validation_service


class ParcelService:
    """Service layer orchestrating Parcel lifecycle, validation, and spatial operations."""

    async def create_parcel(
        self,
        db: AsyncSession,
        data: ParcelCreate,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Parcel:
        # 1. Verify jurisdiction exists
        jur = await jurisdiction_repository.get_by_id(db, data.jurisdiction_id)
        if not jur:
            raise NotFoundException(f"Jurisdiction with ID '{data.jurisdiction_id}' does not exist")

        # 2. Check duplicate identifiers
        existing_code = await parcel_repository.get_by_code(db, data.parcel_code)
        if existing_code:
            raise ConflictException(f"Parcel with code '{data.parcel_code}' already exists")

        existing_number = await parcel_repository.get_by_number_and_jurisdiction(
            db, data.jurisdiction_id, data.parcel_number
        )
        if existing_number:
            raise ConflictException(
                f"Parcel number '{data.parcel_number}' already registered in jurisdiction '{jur.name}'"
            )

        # 3. Spatial validation
        validation = await spatial_validation_service.validate_parcel_candidate(
            db=db,
            geometry_input=data.geometry,
            jurisdiction_id=data.jurisdiction_id,
            source_srid=data.source_srid,
        )
        if not validation.valid:
            error_details = {
                "valid": False,
                "errors": [e.model_dump() for e in validation.errors],
                "warnings": [w.model_dump() for w in validation.warnings],
            }
            raise BadRequestException(
                message=validation.errors[0].message if validation.errors else "Parcel geometry validation failed",
                details=error_details,
            )

        # 4. Parse geometry and compute authoritative measurements
        parsed_geom = GeometryEngine.parse_geometry(data.geometry, source_srid=data.source_srid)
        area_m2 = GeometryEngine.calculate_geodesic_area(parsed_geom)
        centroid_lon, centroid_lat = GeometryEngine.calculate_centroid(parsed_geom)
        geom_wkt = GeometryEngine.to_wkt(parsed_geom)

        # 5. Persist Parcel
        parcel = Parcel(
            jurisdiction_id=data.jurisdiction_id,
            parcel_number=data.parcel_number.strip(),
            parcel_code=data.parcel_code.strip(),
            survey_number=data.survey_number.strip() if data.survey_number else None,
            subdivision_number=data.subdivision_number.strip() if data.subdivision_number else None,
            land_use=data.land_use.upper(),
            area=area_m2,
            area_unit=data.area_unit,
            status=data.status.upper(),
            ownership_status=data.ownership_status.upper(),
            geometry=geom_wkt,
            geometry_wkt=geom_wkt,
            centroid_lon=centroid_lon,
            centroid_lat=centroid_lat,
            source=data.source,
            source_reference=data.source_reference,
            created_by=actor_id,
            updated_by=actor_id,
        )
        created = await parcel_repository.create(db, parcel)

        # 6. Audit logging
        await audit_repository.log_event(
            db=db,
            action="PARCEL_CREATED",
            entity_type="PARCEL",
            entity_id=str(created.id),
            actor_user_id=actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "parcel_code": created.parcel_code,
                "parcel_number": created.parcel_number,
                "jurisdiction_id": str(created.jurisdiction_id),
                "area_sq_m": created.area,
                "source": created.source,
                "centroid": [centroid_lon, centroid_lat],
            },
        )
        return created

    async def get_parcel(self, db: AsyncSession, id: uuid.UUID) -> Parcel:
        parcel = await parcel_repository.get_by_id_with_relations(db, id)
        if not parcel:
            raise NotFoundException(f"Parcel with ID '{id}' not found")
        return parcel

    async def update_parcel(
        self,
        db: AsyncSession,
        id: uuid.UUID,
        data: ParcelUpdate,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Parcel:
        parcel = await parcel_repository.get_by_id(db, id)
        if not parcel:
            raise NotFoundException(f"Parcel with ID '{id}' not found")

        old_details: Dict[str, Any] = {
            "parcel_code": parcel.parcel_code,
            "status": parcel.status,
            "area": parcel.area,
        }

        # Check unique constraints if updated
        if data.parcel_code and data.parcel_code.strip() != parcel.parcel_code:
            existing = await parcel_repository.get_by_code(db, data.parcel_code)
            if existing and existing.id != id:
                raise ConflictException(f"Parcel with code '{data.parcel_code}' already exists")
            parcel.parcel_code = data.parcel_code.strip()

        if data.parcel_number and data.parcel_number.strip() != parcel.parcel_number:
            existing = await parcel_repository.get_by_number_and_jurisdiction(
                db, parcel.jurisdiction_id, data.parcel_number
            )
            if existing and existing.id != id:
                raise ConflictException(
                    f"Parcel number '{data.parcel_number}' already registered in this jurisdiction"
                )
            parcel.parcel_number = data.parcel_number.strip()

        if data.survey_number is not None:
            parcel.survey_number = data.survey_number.strip() if data.survey_number else None
        if data.subdivision_number is not None:
            parcel.subdivision_number = data.subdivision_number.strip() if data.subdivision_number else None
        if data.land_use:
            parcel.land_use = data.land_use.upper()
        if data.status:
            parcel.status = data.status.upper()
        if data.ownership_status:
            parcel.ownership_status = data.ownership_status.upper()
        if data.source_reference is not None:
            parcel.source_reference = data.source_reference

        geometry_changed = False
        if data.geometry is not None:
            source_srid = data.source_srid or 4326
            validation = await spatial_validation_service.validate_parcel_candidate(
                db=db,
                geometry_input=data.geometry,
                jurisdiction_id=parcel.jurisdiction_id,
                exclude_parcel_id=parcel.id,
                source_srid=source_srid,
            )
            if not validation.valid:
                raise BadRequestException(
                    message=validation.errors[0].message if validation.errors else "Updated geometry is invalid",
                    details={"valid": False, "errors": [e.model_dump() for e in validation.errors]},
                )

            parsed_geom = GeometryEngine.parse_geometry(data.geometry, source_srid=source_srid)
            parcel.area = GeometryEngine.calculate_geodesic_area(parsed_geom)
            parcel.centroid_lon, parcel.centroid_lat = GeometryEngine.calculate_centroid(parsed_geom)
            geom_wkt = GeometryEngine.to_wkt(parsed_geom)
            parcel.geometry = geom_wkt
            parcel.geometry_wkt = geom_wkt
            geometry_changed = True

        parcel.updated_by = actor_id
        await db.flush()
        await db.refresh(parcel)

        # Audit
        action = "GEOMETRY_UPDATED" if geometry_changed else "PARCEL_UPDATED"
        await audit_repository.log_event(
            db=db,
            action=action,
            entity_type="PARCEL",
            entity_id=str(parcel.id),
            actor_user_id=actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "old": old_details,
                "new": {"parcel_code": parcel.parcel_code, "status": parcel.status, "area": parcel.area},
                "geometry_changed": geometry_changed,
            },
        )
        return parcel

    async def delete_parcel(
        self,
        db: AsyncSession,
        id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        parcel = await parcel_repository.get_by_id(db, id)
        if not parcel:
            raise NotFoundException(f"Parcel with ID '{id}' not found")

        parcel_info = {
            "parcel_code": parcel.parcel_code,
            "parcel_number": parcel.parcel_number,
            "jurisdiction_id": str(parcel.jurisdiction_id),
        }
        success = await parcel_repository.delete_by_id(db, id)
        if success:
            await audit_repository.log_event(
                db=db,
                action="PARCEL_DELETED",
                entity_type="PARCEL",
                entity_id=str(id),
                actor_user_id=actor_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details=parcel_info,
            )
        return success

    async def search_parcels(
        self,
        db: AsyncSession,
        jurisdiction_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        land_use: Optional[str] = None,
        query: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Parcel], int]:
        return await parcel_repository.search_and_filter(
            db=db,
            jurisdiction_id=jurisdiction_id,
            status=status,
            land_use=land_use,
            query=query,
            skip=skip,
            limit=limit,
        )

    async def get_parcels_in_bbox(
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
        return await parcel_repository.get_by_bbox(
            db=db,
            min_lon=min_lon,
            min_lat=min_lat,
            max_lon=max_lon,
            max_lat=max_lat,
            jurisdiction_id=jurisdiction_id,
            status=status,
            limit=limit,
        )


parcel_service = ParcelService()

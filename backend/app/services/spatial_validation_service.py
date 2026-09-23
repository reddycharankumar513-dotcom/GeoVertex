import uuid
from typing import Any, Dict, List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from app.gis.geometry import GeometryEngine, ValidationResult, ValidationErrorItem, ValidationWarningItem
from app.models.jurisdiction import Jurisdiction
from app.models.parcel import Parcel
from app.repositories.jurisdiction_repository import jurisdiction_repository
from app.repositories.parcel_repository import parcel_repository
import shapely


class SpatialValidationService:
    """Comprehensive spatial and cadastral validation engine.
    Ensures geometric validity, jurisdiction boundary conformance,
    overlap prohibition, and spatial relationship integrity.
    """

    async def validate_parcel_candidate(
        self,
        db: AsyncSession,
        geometry_input: Union[Dict[str, Any], str],
        jurisdiction_id: uuid.UUID,
        exclude_parcel_id: Optional[uuid.UUID] = None,
        source_srid: int = 4326,
    ) -> ValidationResult:
        # 1. Base geometric integrity check
        base_res = GeometryEngine.validate_geometry(
            geometry_input, expected_type="POLYGON", source_srid=source_srid
        )
        errors = list(base_res.errors)
        warnings = list(base_res.warnings)

        if not base_res.valid:
            return ValidationResult(valid=False, errors=errors, warnings=warnings)

        try:
            candidate_geom = GeometryEngine.parse_geometry(geometry_input, source_srid=source_srid)
        except Exception as e:
            errors.append(ValidationErrorItem(code="PARSE_ERROR", message=str(e)))
            return ValidationResult(valid=False, errors=errors, warnings=warnings)

        # 2. Jurisdiction boundary containment check
        jur = await jurisdiction_repository.get_by_id(db, jurisdiction_id)
        if jur and jur.boundary_wkt:
            try:
                jur_geom = GeometryEngine.parse_geometry(jur.boundary_wkt)
                is_contained, outside_area = GeometryEngine.check_containment(candidate_geom, jur_geom)
                if not is_contained:
                    errors.append(
                        ValidationErrorItem(
                            code="PARCEL_OUTSIDE_JURISDICTION",
                            message=f"Parcel geometry lies outside jurisdiction '{jur.name}' boundary by {outside_area} m²",
                        )
                    )
            except Exception as e:
                warnings.append(
                    ValidationWarningItem(
                        code="JURISDICTION_BOUNDARY_CHECK_FAILED",
                        message=f"Could not verify containment against jurisdiction: {str(e)}",
                    )
                )

        # 3. Parcel-to-parcel overlap check within jurisdiction
        min_lon, min_lat, max_lon, max_lat = GeometryEngine.get_bbox(candidate_geom)
        existing_parcels = await parcel_repository.get_by_bbox(
            db,
            min_lon=min_lon,
            min_lat=min_lat,
            max_lon=max_lon,
            max_lat=max_lat,
            jurisdiction_id=jurisdiction_id,
            status="ACTIVE",
        )

        for p in existing_parcels:
            if exclude_parcel_id and p.id == exclude_parcel_id:
                continue
            if not p.geometry_wkt:
                continue
            try:
                p_geom = GeometryEngine.parse_geometry(p.geometry_wkt)
                overlap_type, overlap_area = GeometryEngine.check_overlap(candidate_geom, p_geom)
                if overlap_type == "INVALID_AREA_OVERLAP":
                    errors.append(
                        ValidationErrorItem(
                            code="PARCEL_AREA_OVERLAP",
                            message=f"Candidate parcel overlaps with existing parcel {p.parcel_code} ({p.parcel_number}) by {overlap_area} m²",
                        )
                    )
            except Exception:
                continue

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    async def validate_building_candidate(
        self,
        db: AsyncSession,
        geometry_input: Union[Dict[str, Any], str],
        parcel_id: Optional[uuid.UUID] = None,
        source_srid: int = 4326,
    ) -> ValidationResult:
        base_res = GeometryEngine.validate_geometry(
            geometry_input, expected_type="POLYGON", source_srid=source_srid
        )
        errors = list(base_res.errors)
        warnings = list(base_res.warnings)

        if not base_res.valid:
            return ValidationResult(valid=False, errors=errors, warnings=warnings)

        if parcel_id:
            parcel = await parcel_repository.get_by_id(db, parcel_id)
            if not parcel:
                errors.append(
                    ValidationErrorItem(
                        code="PARCEL_NOT_FOUND",
                        message=f"Associated parcel with id {parcel_id} not found",
                    )
                )
            elif parcel.geometry_wkt:
                try:
                    b_geom = GeometryEngine.parse_geometry(geometry_input, source_srid=source_srid)
                    p_geom = GeometryEngine.parse_geometry(parcel.geometry_wkt)
                    is_contained, outside_area = GeometryEngine.check_containment(b_geom, p_geom)
                    if not is_contained:
                        warnings.append(
                            ValidationWarningItem(
                                code="BUILDING_OUTSIDE_PARCEL",
                                message=f"Building footprint extends outside parcel boundary by {outside_area} m²",
                            )
                        )
                except Exception as e:
                    warnings.append(
                        ValidationWarningItem(
                            code="PARCEL_CONTAINMENT_CHECK_FAILED",
                            message=str(e),
                        )
                    )

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )


spatial_validation_service = SpatialValidationService()

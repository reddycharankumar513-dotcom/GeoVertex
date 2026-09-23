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

    async def validate_building_3d_candidate(
        self,
        db: AsyncSession,
        height: float,
        height_unit: str = "METERS",
        base_elevation: float = 0.0,
        height_confidence: Optional[float] = None,
        geometry_input: Optional[Union[Dict[str, Any], str]] = None,
        parcel_id: Optional[uuid.UUID] = None,
        source_srid: int = 4326,
    ) -> ValidationResult:
        """Validate 3D building vertical parameters and relationship to parcel."""
        errors: List[ValidationErrorItem] = []
        warnings: List[ValidationWarningItem] = []

        # 1. Height validation
        if height is None or height < 0:
            errors.append(
                ValidationErrorItem(
                    code="INVALID_BUILDING_HEIGHT",
                    message="Building height must be a non-negative number.",
                )
            )

        allowed_units = {"METERS", "FEET"}
        if height_unit and height_unit.upper() not in allowed_units:
            errors.append(
                ValidationErrorItem(
                    code="INVALID_HEIGHT_UNIT",
                    message=f"Unsupported height unit '{height_unit}'. Allowed units: {list(allowed_units)}",
                )
            )

        if height_confidence is not None and not (0.0 <= height_confidence <= 1.0):
            warnings.append(
                ValidationWarningItem(
                    code="INVALID_CONFIDENCE_SCORE",
                    message="Height confidence score should be between 0.0 and 1.0",
                )
            )

        if base_elevation is not None and (base_elevation < -500.0 or base_elevation > 9000.0):
            warnings.append(
                ValidationWarningItem(
                    code="EXTREME_BASE_ELEVATION",
                    message=f"Base elevation {base_elevation}m is outside standard terrestrial ranges.",
                )
            )

        # 2. Footprint & parcel containment if geometry is provided
        if geometry_input:
            footprint_res = await self.validate_building_candidate(
                db=db,
                geometry_input=geometry_input,
                parcel_id=parcel_id,
                source_srid=source_srid,
            )
            errors.extend(footprint_res.errors)
            warnings.extend(footprint_res.warnings)

            # Check if building footprint crosses multiple parcels
            cross_warnings = await self.check_building_crosses_parcels(
                db=db,
                geometry_input=geometry_input,
                primary_parcel_id=parcel_id,
                source_srid=source_srid,
            )
            warnings.extend(cross_warnings)

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    async def check_building_crosses_parcels(
        self,
        db: AsyncSession,
        geometry_input: Union[Dict[str, Any], str],
        primary_parcel_id: Optional[uuid.UUID] = None,
        source_srid: int = 4326,
    ) -> List[ValidationWarningItem]:
        """Detect whether building footprint crosses multiple cadastral parcels."""
        warnings: List[ValidationWarningItem] = []
        try:
            b_geom = GeometryEngine.parse_geometry(geometry_input, source_srid=source_srid)
            min_x, min_y, max_x, max_y = b_geom.bounds
            bbox_str = f"{min_x},{min_y},{max_x},{max_y}"

            # Query nearby parcels
            intersecting_parcels = await parcel_repository.get_in_bbox(db, bbox_str)
            crossing_parcels = []

            for p in intersecting_parcels:
                if not p.geometry_wkt:
                    continue
                try:
                    p_geom = GeometryEngine.parse_geometry(p.geometry_wkt)
                    if b_geom.intersects(p_geom):
                        intersection = b_geom.intersection(p_geom)
                        # More than minimal vertex touching (> 0.5 sq m area)
                        if intersection.area > 0.00000001:
                            crossing_parcels.append(p.parcel_code)
                except Exception:
                    continue

            if len(crossing_parcels) > 1:
                warnings.append(
                    ValidationWarningItem(
                        code="BUILDING_CROSSES_PARCELS",
                        message=f"Building footprint intersects multiple cadastral parcels: {', '.join(crossing_parcels)}",
                        details={"intersecting_parcel_codes": crossing_parcels},
                    )
                )
        except Exception as e:
            warnings.append(
                ValidationWarningItem(
                    code="PARCEL_CROSSING_CHECK_ERROR",
                    message=f"Failed to check parcel crossing: {str(e)}",
                )
            )

        return warnings


spatial_validation_service = SpatialValidationService()


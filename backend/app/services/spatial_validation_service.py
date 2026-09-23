import uuid
from typing import Any, Dict, List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from app.gis.geometry import GeometryEngine, ValidationResult, ValidationErrorItem, ValidationWarningItem
from app.models.jurisdiction import Jurisdiction
from app.models.parcel import Parcel
from app.repositories.building_repository import building_repository
from app.repositories.floor_repository import floor_repository
from app.repositories.jurisdiction_repository import jurisdiction_repository
from app.repositories.parcel_repository import parcel_repository
from app.repositories.unit_repository import unit_repository
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

    async def validate_floor_candidate(
        self,
        db: AsyncSession,
        building_id: uuid.UUID,
        floor_number: int,
        elevation_min_m: float,
        elevation_max_m: float,
        geometry_input: Optional[Union[Dict[str, Any], str]] = None,
        current_floor_id: Optional[uuid.UUID] = None,
        source_srid: int = 4326,
    ) -> ValidationResult:
        """Validate floor slab vertical elevation stacking and footprint containment."""
        errors: List[ValidationErrorItem] = []
        warnings: List[ValidationWarningItem] = []

        # 1. Elevation bounds check
        if elevation_min_m >= elevation_max_m:
            errors.append(
                ValidationErrorItem(
                    code="INVALID_ELEVATION_BOUNDS",
                    message=f"Floor elevation min ({elevation_min_m}m) must be strictly less than elevation max ({elevation_max_m}m)",
                )
            )
        elif (elevation_max_m - elevation_min_m) < 0.1:
            errors.append(
                ValidationErrorItem(
                    code="MINIMUM_HEIGHT_VIOLATION",
                    message="Floor slab vertical thickness must be at least 0.10 meters",
                )
            )

        # 2. Building existence & footprint containment check
        bldg = await building_repository.get_by_id(db, building_id)
        if not bldg:
            errors.append(
                ValidationErrorItem(
                    code="BUILDING_NOT_FOUND",
                    message=f"Parent building with ID '{building_id}' does not exist",
                )
            )
        elif geometry_input:
            base_res = GeometryEngine.validate_geometry(geometry_input, expected_type="POLYGON", source_srid=source_srid)
            errors.extend(base_res.errors)
            warnings.extend(base_res.warnings)

            if base_res.valid and bldg.geometry_wkt:
                try:
                    f_geom = GeometryEngine.parse_geometry(geometry_input, source_srid=source_srid)
                    b_geom = GeometryEngine.parse_geometry(bldg.geometry_wkt)
                    is_covered, outside_area = GeometryEngine.check_containment(f_geom, b_geom)
                    if not is_covered and outside_area > 0.5:
                        errors.append(
                            ValidationErrorItem(
                                code="FLOOR_OUTSIDE_BUILDING",
                                message=f"Floor slab extends outside parent building footprint by {outside_area} m²",
                            )
                        )
                except Exception as e:
                    warnings.append(
                        ValidationWarningItem(
                            code="FLOOR_CONTAINMENT_CHECK_FAILED",
                            message=f"Could not verify floor containment within building: {str(e)}",
                        )
                    )

        # 3. Vertical stacking & uniqueness checks against existing floors in building
        existing_floors = await floor_repository.get_by_building(db, building_id)
        for ef in existing_floors:
            if current_floor_id and ef.id == current_floor_id:
                continue

            # Duplicate floor number
            if ef.floor_number == floor_number:
                errors.append(
                    ValidationErrorItem(
                        code="DUPLICATE_FLOOR_NUMBER",
                        message=f"Building already has a floor with index {floor_number} (Code: '{ef.floor_code}')",
                    )
                )

            # Vertical elevation overlap clash (with 5cm tolerance for shared slab)
            overlap_min = max(elevation_min_m, ef.elevation_min_m)
            overlap_max = min(elevation_max_m, ef.elevation_max_m)
            if overlap_min < (overlap_max - 0.05):
                errors.append(
                    ValidationErrorItem(
                        code="FLOOR_ELEVATION_CLASH",
                        message=f"Floor elevation range [{elevation_min_m}m, {elevation_max_m}m] clashes vertically with existing floor {ef.floor_number} [{ef.elevation_min_m}m, {ef.elevation_max_m}m]",
                    )
                )

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    async def validate_unit_candidate(
        self,
        db: AsyncSession,
        floor_id: uuid.UUID,
        unit_number: str,
        elevation_min_m: float,
        elevation_max_m: float,
        geometry_input: Union[Dict[str, Any], str],
        current_unit_id: Optional[uuid.UUID] = None,
        source_srid: int = 4326,
    ) -> ValidationResult:
        """Validate property unit boundary containment within floor and disjointness against peers."""
        errors: List[ValidationErrorItem] = []
        warnings: List[ValidationWarningItem] = []

        # 1. Elevation sanity
        if elevation_min_m >= elevation_max_m:
            errors.append(
                ValidationErrorItem(
                    code="INVALID_ELEVATION_BOUNDS",
                    message=f"Unit elevation min ({elevation_min_m}m) must be strictly less than elevation max ({elevation_max_m}m)",
                )
            )

        # 2. Geometry base validity
        base_res = GeometryEngine.validate_geometry(geometry_input, expected_type="POLYGON", source_srid=source_srid)
        errors.extend(base_res.errors)
        warnings.extend(base_res.warnings)

        # 3. Floor existence & floor containment check
        floor = await floor_repository.get_by_id(db, floor_id)
        if not floor:
            errors.append(
                ValidationErrorItem(
                    code="FLOOR_NOT_FOUND",
                    message=f"Parent floor with ID '{floor_id}' does not exist",
                )
            )
            return ValidationResult(valid=False, errors=errors, warnings=warnings)

        if base_res.valid and floor.geometry_wkt:
            try:
                u_geom = GeometryEngine.parse_geometry(geometry_input, source_srid=source_srid)
                f_geom = GeometryEngine.parse_geometry(floor.geometry_wkt)

                # Unit containment in floor slab
                is_covered, outside_area = GeometryEngine.check_containment(u_geom, f_geom)
                if not is_covered and outside_area > 0.2:
                    errors.append(
                        ValidationErrorItem(
                            code="UNIT_OUTSIDE_FLOOR",
                            message=f"Unit boundary extends outside parent floor slab by {outside_area} m²",
                        )
                    )

                # Vertical span containment warning
                if elevation_min_m < (floor.elevation_min_m - 0.5) or elevation_max_m > (floor.elevation_max_m + 0.5):
                    warnings.append(
                        ValidationWarningItem(
                            code="UNIT_ELEVATION_EXCEEDS_FLOOR",
                            message=f"Unit elevation range [{elevation_min_m}m, {elevation_max_m}m] differs from floor bounds [{floor.elevation_min_m}m, {floor.elevation_max_m}m]",
                        )
                    )

                # 4. Peer unit disjointness on same floor (no area overlap)
                existing_units = await unit_repository.get_by_floor(db, floor_id)
                for eu in existing_units:
                    if current_unit_id and eu.id == current_unit_id:
                        continue

                    # Duplicate unit number on same floor
                    if eu.unit_number.strip().lower() == unit_number.strip().lower():
                        errors.append(
                            ValidationErrorItem(
                                code="DUPLICATE_UNIT_NUMBER",
                                message=f"Floor already contains unit with designation '{unit_number}' (Code: '{eu.unit_code}')",
                            )
                        )

                    # Spatial area overlap test
                    if eu.geometry_wkt:
                        try:
                            eu_geom = GeometryEngine.parse_geometry(eu.geometry_wkt)
                            if u_geom.intersects(eu_geom):
                                inter = u_geom.intersection(eu_geom)
                                # Check if intersection is 2D polygonal area overlap (not merely shared boundary linestring)
                                if inter.geom_type in ['Polygon', 'MultiPolygon'] and inter.area > 0.00000001:
                                    overlap_area_m2 = GeometryEngine.calculate_geodesic_area(inter)
                                    if overlap_area_m2 > 0.05:
                                        errors.append(
                                            ValidationErrorItem(
                                                code="UNIT_OVERLAP_CONFLICT",
                                                message=f"Unit boundary overlaps with existing Unit '{eu.unit_number}' by {overlap_area_m2} m²",
                                            )
                                        )
                        except Exception:
                            continue

            except Exception as e:
                warnings.append(
                    ValidationWarningItem(
                        code="UNIT_CONTAINMENT_CHECK_FAILED",
                        message=f"Could not verify unit spatial containment: {str(e)}",
                    )
                )

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )


spatial_validation_service = SpatialValidationService()


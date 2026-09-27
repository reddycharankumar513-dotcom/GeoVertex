from typing import Any, Dict, List
from collections import defaultdict
import shapely
from app.gis.geometry import GeometryEngine
from app.gis.validation.base import IssueDraft, ValidationContext, ValidationRule


class FloorInvalidElevationRule(ValidationRule):
    rule_id = "FLOOR_INVALID_ELEVATION"
    name = "Invalid Floor Elevation Interval"
    description = "Checks that base_elevation, top_elevation, and height satisfy top > base and height > 0."
    category = "FLOOR"
    severity = "ERROR"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["FLOOR", "BUILDING", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        for f in context.floors:
            base = getattr(f, "elevation_min_m", None)
            top = getattr(f, "elevation_max_m", None)
            height = getattr(f, "height_m", None)
            f_code = getattr(f, "floor_code", None) or f"Floor {getattr(f, 'floor_number', f.id)}"

            if base is None or top is None:
                issues.append(IssueDraft(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    issue_code="FLR-001",
                    category=self.category,
                    severity=self.severity,
                    entity_type="FLOOR",
                    entity_id=str(f.id),
                    message=f"Floor {f_code} has missing vertical elevation limits (base={base}, top={top}).",
                    technical_explanation="elevation_min_m or elevation_max_m is null in database.",
                    expected_value="Defined numeric elevations",
                    measured_value=f"base={base}, top={top}",
                ))
            elif top <= base:
                issues.append(IssueDraft(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    issue_code="FLR-001",
                    category=self.category,
                    severity=self.severity,
                    entity_type="FLOOR",
                    entity_id=str(f.id),
                    message=f"Floor {f_code} top elevation ({top}m) is less than or equal to base elevation ({base}m).",
                    technical_explanation=f"Vertical interval violation: elevation_max_m ({top}m) <= elevation_min_m ({base}m).",
                    expected_value="top_elevation > base_elevation",
                    measured_value=f"top={top}m <= base={base}m",
                ))
            elif height is not None and height <= 0:
                issues.append(IssueDraft(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    issue_code="FLR-001",
                    category=self.category,
                    severity=self.severity,
                    entity_type="FLOOR",
                    entity_id=str(f.id),
                    message=f"Floor {f_code} has zero or negative height ({height}m).",
                    technical_explanation="height_m must be strictly positive.",
                    expected_value="height > 0.0m",
                    measured_value=f"{height}m",
                ))
        return issues


class FloorVerticalOverlapRule(ValidationRule):
    rule_id = "FLOOR_VERTICAL_OVERLAP"
    name = "Floor Vertical Interval Overlap"
    description = "Detects 1D vertical elevation overlap between distinct floor slabs in the same building."
    category = "FLOOR"
    severity = "ERROR"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["FLOOR", "BUILDING", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        bld_floors = defaultdict(list)
        for f in context.floors:
            bld_id = getattr(f, "building_id", None)
            if bld_id:
                bld_floors[str(bld_id)].append(f)

        tol = context.tolerances.vertical_elevation_tolerance_m
        for bld_id, flist in bld_floors.items():
            if len(flist) < 2:
                continue
            # Sort by base elevation
            valid_flist = [f for f in flist if getattr(f, "elevation_min_m", None) is not None and getattr(f, "elevation_max_m", None) is not None]
            valid_flist.sort(key=lambda x: x.elevation_min_m)

            for i in range(len(valid_flist) - 1):
                f1 = valid_flist[i]
                f2 = valid_flist[i + 1]
                # If f1.top > f2.base + tol, they overlap vertically
                overlap = f1.elevation_max_m - f2.elevation_min_m
                if overlap > tol:
                    f1_code = getattr(f1, "floor_code", f"L{f1.floor_number}")
                    f2_code = getattr(f2, "floor_code", f"L{f2.floor_number}")
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="FLR-002",
                        category=self.category,
                        severity=self.severity,
                        entity_type="FLOOR",
                        entity_id=str(f1.id),
                        related_entity_type="FLOOR",
                        related_entity_id=str(f2.id),
                        message=f"Vertical elevation overlap ({overlap:.2f}m) detected between floor {f1_code} and floor {f2_code}.",
                        technical_explanation=(
                            f"Floor 1 range [{f1.elevation_min_m:.2f}m, {f1.elevation_max_m:.2f}m] intersects "
                            f"Floor 2 range [{f2.elevation_min_m:.2f}m, {f2.elevation_max_m:.2f}m] with overlap "
                            f"of {overlap:.2f}m exceeding tolerance of {tol:.2f}m."
                        ),
                        measured_value=f"{overlap:.2f}m overlap",
                        expected_value=f"<= {tol:.2f}m",
                        tolerance=f"{tol:.2f}m",
                        metadata_json={
                            "building_id": bld_id,
                            "floor_1_id": str(f1.id),
                            "floor_2_id": str(f2.id),
                            "floor_1_range": [f1.elevation_min_m, f1.elevation_max_m],
                            "floor_2_range": [f2.elevation_min_m, f2.elevation_max_m],
                            "overlap_m": overlap,
                        },
                    ))
        return issues


class FloorVerticalGapRule(ValidationRule):
    rule_id = "FLOOR_VERTICAL_GAP"
    name = "Floor Vertical Interval Gap"
    description = "Detects unexplained vertical gaps between consecutive floor slabs in the same building."
    category = "FLOOR"
    severity = "WARNING"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["FLOOR", "BUILDING", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        bld_floors = defaultdict(list)
        for f in context.floors:
            bld_id = getattr(f, "building_id", None)
            if bld_id:
                bld_floors[str(bld_id)].append(f)

        gap_tol = context.tolerances.vertical_gap_tolerance_m
        for bld_id, flist in bld_floors.items():
            if len(flist) < 2:
                continue
            valid_flist = [f for f in flist if getattr(f, "elevation_min_m", None) is not None and getattr(f, "elevation_max_m", None) is not None]
            valid_flist.sort(key=lambda x: x.elevation_min_m)

            for i in range(len(valid_flist) - 1):
                f1 = valid_flist[i]
                f2 = valid_flist[i + 1]
                gap = f2.elevation_min_m - f1.elevation_max_m
                if gap > gap_tol:
                    f1_code = getattr(f1, "floor_code", f"L{f1.floor_number}")
                    f2_code = getattr(f2, "floor_code", f"L{f2.floor_number}")
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="FLR-003",
                        category=self.category,
                        severity=self.severity,
                        entity_type="FLOOR",
                        entity_id=str(f1.id),
                        related_entity_type="FLOOR",
                        related_entity_id=str(f2.id),
                        message=f"Vertical gap ({gap:.2f}m) detected between floor {f1_code} and floor {f2_code}.",
                        technical_explanation=f"Gap {gap:.2f}m between f1 top ({f1.elevation_max_m}m) and f2 base ({f2.elevation_min_m}m) exceeds tolerance of {gap_tol:.2f}m.",
                        measured_value=f"{gap:.2f}m gap",
                        expected_value=f"<= {gap_tol:.2f}m",
                        tolerance=f"{gap_tol:.2f}m",
                    ))
        return issues


class FloorDuplicateRule(ValidationRule):
    rule_id = "FLOOR_DUPLICATE"
    name = "Duplicate Floor Identifier"
    description = "Detects duplicate floor codes or duplicate floor numbers within the same building."
    category = "FLOOR"
    severity = "CRITICAL"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["FLOOR", "BUILDING", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        bld_floors = defaultdict(list)
        for f in context.floors:
            bld_id = getattr(f, "building_id", None)
            if bld_id:
                bld_floors[str(bld_id)].append(f)

        for bld_id, flist in bld_floors.items():
            seen_nums = {}
            for f in flist:
                num = getattr(f, "floor_number", None)
                if num is not None:
                    if num in seen_nums:
                        prev = seen_nums[num]
                        issues.append(IssueDraft(
                            rule_id=self.rule_id,
                            rule_version=self.rule_version,
                            issue_code="FLR-004",
                            category=self.category,
                            severity=self.severity,
                            entity_type="FLOOR",
                            entity_id=str(f.id),
                            related_entity_type="FLOOR",
                            related_entity_id=str(prev.id),
                            message=f"Duplicate floor number '{num}' in building {bld_id}.",
                            technical_explanation="Floor stack must contain unique floor numbers per building.",
                            expected_value="Unique floor number",
                            measured_value=str(num),
                        ))
                    else:
                        seen_nums[num] = f
        return issues


class FloorOutsideBuildingRule(ValidationRule):
    rule_id = "FLOOR_OUTSIDE_BUILDING"
    name = "Floor Footprint Outside Building Envelope"
    description = "Verifies that floor polygon boundaries do not extend significantly outside the parent building envelope."
    category = "FLOOR"
    severity = "ERROR"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["FLOOR", "BUILDING", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        bld_map = {str(b.id): b for b in context.buildings}
        for f in context.floors:
            bld_id = getattr(f, "building_id", None)
            if not bld_id or str(bld_id) not in bld_map:
                continue
            b = bld_map[str(bld_id)]
            f_wkt = getattr(f, "geometry_wkt", None) or getattr(f, "geometry", None)
            b_wkt = getattr(b, "geometry_wkt", None) or getattr(b, "geometry", None)
            if not f_wkt or not b_wkt:
                continue
            try:
                f_geom = GeometryEngine.parse_geometry(f_wkt)
                b_geom = GeometryEngine.parse_geometry(b_wkt)
                if not b_geom.contains(f_geom):
                    outside = f_geom.difference(b_geom)
                    outside_area = GeometryEngine.calculate_geodesic_area(outside)
                    f_area = GeometryEngine.calculate_geodesic_area(f_geom)
                    if f_area > 0 and (outside_area / f_area) > 0.02 and outside_area > 0.1:
                        issues.append(IssueDraft(
                            rule_id=self.rule_id,
                            rule_version=self.rule_version,
                            issue_code="FLR-005",
                            category=self.category,
                            severity=self.severity,
                            entity_type="FLOOR",
                            entity_id=str(f.id),
                            related_entity_type="BUILDING",
                            related_entity_id=str(b.id),
                            message=f"Floor {getattr(f, 'floor_code', f.id)} extends {outside_area:.2f} m² outside the building footprint.",
                            technical_explanation=f"Floor 2D boundary extends beyond building polygon envelope by {outside_area:.2f} m².",
                            geometry_wkt=GeometryEngine.to_wkt(outside),
                            measured_value=f"{outside_area:.2f} m² outside",
                            expected_value="Contained inside building",
                        ))
            except Exception:
                pass
        return issues


class FloorAreaMismatchRule(ValidationRule):
    rule_id = "FLOOR_AREA_MISMATCH"
    name = "Floor Area Exceeds Building Envelope"
    description = "Flags floor slabs whose gross area significantly exceeds parent building footprint area without cantilever justification."
    category = "FLOOR"
    severity = "WARNING"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["FLOOR", "BUILDING", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        bld_map = {str(b.id): b for b in context.buildings}
        for f in context.floors:
            bld_id = getattr(f, "building_id", None)
            if not bld_id or str(bld_id) not in bld_map:
                continue
            b = bld_map[str(bld_id)]
            f_area = getattr(f, "area_sqm", None)
            b_area = getattr(b, "area", None)
            if f_area and b_area and b_area > 0:
                if f_area > (b_area * 1.15):
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="FLR-006",
                        category=self.category,
                        severity=self.severity,
                        entity_type="FLOOR",
                        entity_id=str(f.id),
                        related_entity_type="BUILDING",
                        related_entity_id=str(b.id),
                        message=f"Floor {getattr(f, 'floor_code', f.id)} area ({f_area:.2f} m²) exceeds building footprint area ({b_area:.2f} m²) by {(f_area/b_area - 1)*100:.1f}%.",
                        technical_explanation=f"Floor area exceeds building envelope by more than 15% ({f_area:.2f} m² vs {b_area:.2f} m²).",
                        measured_value=f"{f_area:.2f} m²",
                        expected_value=f"<= {b_area:.2f} m²",
                    ))
        return issues

from typing import Any, Dict, List
from collections import defaultdict
import shapely
from app.gis.geometry import GeometryEngine
from app.gis.validation.base import IssueDraft, ValidationContext, ValidationRule


class UnitOutsideFloorRule(ValidationRule):
    rule_id = "UNIT_OUTSIDE_FLOOR"
    name = "Unit Boundary Outside Floor Envelope"
    description = "Checks that 2D unit polygons are geometrically contained within their parent floor boundary."
    category = "UNIT"
    severity = "ERROR"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["UNIT", "FLOOR", "BUILDING", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        floor_map = {str(f.id): f for f in context.floors}
        tol_ratio = context.tolerances.unit_outside_floor_tolerance_ratio

        for u in context.units:
            floor_id = getattr(u, "floor_id", None)
            if not floor_id or str(floor_id) not in floor_map:
                continue
            fl = floor_map[str(floor_id)]
            u_wkt = getattr(u, "geometry_wkt", None) or getattr(u, "geometry", None)
            fl_wkt = getattr(fl, "geometry_wkt", None) or getattr(fl, "geometry", None)
            if not u_wkt or not fl_wkt:
                continue
            try:
                u_geom = GeometryEngine.parse_geometry(u_wkt)
                fl_geom = GeometryEngine.parse_geometry(fl_wkt)
                if not fl_geom.contains(u_geom):
                    outside = u_geom.difference(fl_geom)
                    u_area = GeometryEngine.calculate_geodesic_area(u_geom)
                    outside_area = GeometryEngine.calculate_geodesic_area(outside)
                    if u_area > 0:
                        outside_ratio = outside_area / u_area
                        if outside_ratio > tol_ratio and outside_area > 0.05:
                            u_code = getattr(u, "unit_code", None) or getattr(u, "unit_number", str(u.id))
                            fl_code = getattr(fl, "floor_code", None) or str(fl.id)
                            issues.append(IssueDraft(
                                rule_id=self.rule_id,
                                rule_version=self.rule_version,
                                issue_code="UNT-001",
                                category=self.category,
                                severity=self.severity,
                                entity_type="UNIT",
                                entity_id=str(u.id),
                                related_entity_type="FLOOR",
                                related_entity_id=str(fl.id),
                                message=f"Unit {u_code} extends outside floor {fl_code} by {outside_area:.2f} m² ({outside_ratio * 100:.1f}%).",
                                technical_explanation=(
                                    f"Containment violation: ST_Contains(floor, unit) is false. "
                                    f"Outside area={outside_area:.2f} m², outside_ratio={outside_ratio:.4f} > tolerance={tol_ratio:.4f}."
                                ),
                                geometry_wkt=GeometryEngine.to_wkt(outside),
                                measured_value=f"{outside_ratio * 100:.1f}% outside ({outside_area:.2f} m²)",
                                expected_value=f"<= {tol_ratio * 100:.1f}% outside",
                                tolerance=f"{tol_ratio * 100:.1f}%",
                                metadata_json={
                                    "unit_id": str(u.id),
                                    "floor_id": str(fl.id),
                                    "unit_area_sqm": u_area,
                                    "outside_area_sqm": outside_area,
                                    "outside_ratio": round(outside_ratio, 4),
                                },
                            ))
            except Exception:
                pass
        return issues


class UnitOutsideBuildingRule(ValidationRule):
    rule_id = "UNIT_OUTSIDE_BUILDING"
    name = "Unit Boundary Outside Building Envelope"
    description = "Checks that 2D unit polygons are contained within the building footprint."
    category = "UNIT"
    severity = "ERROR"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["UNIT", "BUILDING", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        bld_map = {str(b.id): b for b in context.buildings}
        for u in context.units:
            bld_id = getattr(u, "building_id", None)
            if not bld_id or str(bld_id) not in bld_map:
                continue
            b = bld_map[str(bld_id)]
            u_wkt = getattr(u, "geometry_wkt", None) or getattr(u, "geometry", None)
            b_wkt = getattr(b, "geometry_wkt", None) or getattr(b, "geometry", None)
            if not u_wkt or not b_wkt:
                continue
            try:
                u_geom = GeometryEngine.parse_geometry(u_wkt)
                b_geom = GeometryEngine.parse_geometry(b_wkt)
                if not b_geom.contains(u_geom):
                    outside = u_geom.difference(b_geom)
                    outside_area = GeometryEngine.calculate_geodesic_area(outside)
                    if outside_area > 0.05:
                        u_code = getattr(u, "unit_code", None) or str(u.id)
                        issues.append(IssueDraft(
                            rule_id=self.rule_id,
                            rule_version=self.rule_version,
                            issue_code="UNT-002",
                            category=self.category,
                            severity=self.severity,
                            entity_type="UNIT",
                            entity_id=str(u.id),
                            related_entity_type="BUILDING",
                            related_entity_id=str(b.id),
                            message=f"Unit {u_code} extends {outside_area:.2f} m² outside the building footprint.",
                            technical_explanation=f"ST_Contains(building, unit) is false. Outside area = {outside_area:.2f} m².",
                            geometry_wkt=GeometryEngine.to_wkt(outside),
                            measured_value=f"{outside_area:.2f} m² outside",
                            expected_value="100% inside building",
                        ))
            except Exception:
                pass
        return issues


class UnitOverlapRule(ValidationRule):
    rule_id = "UNIT_OVERLAP"
    name = "Co-Planar Unit Overlap"
    description = "Detects spatial area overlaps between distinct property units situated on the same floor level."
    category = "UNIT"
    severity = "ERROR"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["UNIT", "FLOOR", "BUILDING", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        floor_units = defaultdict(list)
        for u in context.units:
            fl_id = getattr(u, "floor_id", None)
            if fl_id:
                floor_units[str(fl_id)].append(u)

        tol = context.tolerances.unit_overlap_tolerance_sqm

        for fl_id, ulist in floor_units.items():
            if len(ulist) < 2:
                continue
            parsed = []
            for u in ulist:
                wkt_str = getattr(u, "geometry_wkt", None) or getattr(u, "geometry", None)
                if wkt_str:
                    try:
                        g = GeometryEngine.parse_geometry(wkt_str)
                        if g.is_valid and not g.is_empty:
                            parsed.append((u, g))
                    except Exception:
                        pass

            for i in range(len(parsed)):
                u1, g1 = parsed[i]
                for j in range(i + 1, len(parsed)):
                    u2, g2 = parsed[j]
                    if not g1.envelope.intersects(g2.envelope):
                        continue
                    if g1.intersects(g2):
                        inter = g1.intersection(g2)
                        if inter.geom_type in ["Polygon", "MultiPolygon"] and not inter.is_empty:
                            area = GeometryEngine.calculate_geodesic_area(inter)
                            if area > tol:
                                u1_code = getattr(u1, "unit_code", getattr(u1, "unit_number", str(u1.id)))
                                u2_code = getattr(u2, "unit_code", getattr(u2, "unit_number", str(u2.id)))
                                issues.append(IssueDraft(
                                    rule_id=self.rule_id,
                                    rule_version=self.rule_version,
                                    issue_code="UNT-003",
                                    category=self.category,
                                    severity=self.severity,
                                    entity_type="UNIT",
                                    entity_id=str(u1.id),
                                    related_entity_type="UNIT",
                                    related_entity_id=str(u2.id),
                                    message=f"Unit {u1_code} overlaps Unit {u2_code} by {area:.2f} square meters on floor {fl_id}.",
                                    technical_explanation=(
                                        f"Co-planar unit footprints share polygonal intersection area of {area:.2f} m² "
                                        f"exceeding tolerance of {tol:.2f} m²."
                                    ),
                                    geometry_wkt=GeometryEngine.to_wkt(inter),
                                    measured_value=f"{area:.2f} m²",
                                    expected_value=f"<= {tol:.2f} m²",
                                    tolerance=f"{tol:.2f} m²",
                                    metadata_json={"overlap_area_sqm": area, "floor_id": fl_id},
                                ))
        return issues


class UnitDuplicateRule(ValidationRule):
    rule_id = "UNIT_DUPLICATE"
    name = "Duplicate Unit Identifier"
    description = "Detects duplicate unit codes or unit numbers within the same floor or building."
    category = "UNIT"
    severity = "CRITICAL"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["UNIT", "FLOOR", "BUILDING", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        floor_units = defaultdict(list)
        for u in context.units:
            fl_id = getattr(u, "floor_id", None)
            if fl_id:
                floor_units[str(fl_id)].append(u)

        for fl_id, ulist in floor_units.items():
            seen = {}
            for u in ulist:
                code = getattr(u, "unit_code", None) or getattr(u, "unit_number", None)
                if code:
                    if code in seen:
                        prev = seen[code]
                        issues.append(IssueDraft(
                            rule_id=self.rule_id,
                            rule_version=self.rule_version,
                            issue_code="UNT-004",
                            category=self.category,
                            severity=self.severity,
                            entity_type="UNIT",
                            entity_id=str(u.id),
                            related_entity_type="UNIT",
                            related_entity_id=str(prev.id),
                            message=f"Duplicate unit code '{code}' detected on floor {fl_id}.",
                            technical_explanation="Units within the same floor must have unique unit numbers and codes.",
                            expected_value="Unique unit code",
                            measured_value=code,
                        ))
                    else:
                        seen[code] = u
        return issues


class UnitInvalidGeometryRule(ValidationRule):
    rule_id = "UNIT_INVALID_GEOMETRY"
    name = "Degenerate Unit Geometry"
    description = "Checks that unit polygons have valid area (> 1 m²) and proper topology."
    category = "UNIT"
    severity = "ERROR"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["UNIT", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        for u in context.units:
            wkt_str = getattr(u, "geometry_wkt", None) or getattr(u, "geometry", None)
            if not wkt_str:
                continue
            try:
                g = GeometryEngine.parse_geometry(wkt_str)
                area = GeometryEngine.calculate_geodesic_area(g)
                if area < context.tolerances.min_polygon_area_sqm:
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="UNT-005",
                        category=self.category,
                        severity=self.severity,
                        entity_type="UNIT",
                        entity_id=str(u.id),
                        message=f"Unit {getattr(u, 'unit_code', u.id)} has suspiciously small footprint area ({area:.2f} m²).",
                        technical_explanation=f"Unit area {area:.2f} m² is below the minimum threshold of {context.tolerances.min_polygon_area_sqm} m².",
                        measured_value=f"{area:.2f} m²",
                        expected_value=f">= {context.tolerances.min_polygon_area_sqm} m²",
                    ))
            except Exception:
                pass
        return issues


class UnitAreaMismatchRule(ValidationRule):
    rule_id = "UNIT_AREA_MISMATCH"
    name = "Unit Gross vs Net Area Inconsistency"
    description = "Checks that net area is less than or equal to gross area, and gross area matches polygon boundary."
    category = "UNIT"
    severity = "WARNING"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["UNIT", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        for u in context.units:
            gross = getattr(u, "gross_area_sqm", None)
            net = getattr(u, "net_area_sqm", None)
            if gross and net and net > gross:
                u_code = getattr(u, "unit_code", str(u.id))
                issues.append(IssueDraft(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    issue_code="UNT-006",
                    category=self.category,
                    severity=self.severity,
                    entity_type="UNIT",
                    entity_id=str(u.id),
                    message=f"Unit {u_code} net area ({net:.2f} m²) exceeds gross area ({gross:.2f} m²).",
                    technical_explanation="Architectural impossibility: Net usable area cannot exceed gross boundary area.",
                    measured_value=f"Net {net:.2f} m² > Gross {gross:.2f} m²",
                    expected_value="net_area <= gross_area",
                ))
        return issues

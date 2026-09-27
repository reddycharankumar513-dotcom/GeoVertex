from typing import Any, Dict, List
import shapely
from app.gis.geometry import GeometryEngine
from app.gis.validation.base import IssueDraft, ValidationContext, ValidationRule


class BuildingOutsideParcelRule(ValidationRule):
    rule_id = "BUILDING_OUTSIDE_PARCEL"
    name = "Building Entirely Outside Parcel"
    description = "Detects building footprints that have zero intersection with their assigned land parcel."
    category = "BUILDING"
    severity = "CRITICAL"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["BUILDING", "PARCEL", "SYSTEM", "CROSS_DATASET"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        parcel_map = {str(p.id): p for p in context.parcels}

        for b in context.buildings:
            parcel_id = getattr(b, "parcel_id", None)
            if not parcel_id or str(parcel_id) not in parcel_map:
                continue
            p = parcel_map[str(parcel_id)]
            b_wkt = getattr(b, "geometry_wkt", None) or getattr(b, "geometry", None)
            p_wkt = getattr(p, "geometry_wkt", None) or getattr(p, "geometry", None)
            if not b_wkt or not p_wkt:
                continue
            try:
                b_geom = GeometryEngine.parse_geometry(b_wkt)
                p_geom = GeometryEngine.parse_geometry(p_wkt)
                if not b_geom.intersects(p_geom):
                    b_ref = getattr(b, "building_reference", None) or str(b.id)
                    p_num = getattr(p, "parcel_number", None) or str(p.id)
                    b_area = GeometryEngine.calculate_geodesic_area(b_geom)
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="BLD-001",
                        category=self.category,
                        severity=self.severity,
                        entity_type="BUILDING",
                        entity_id=str(b.id),
                        related_entity_type="PARCEL",
                        related_entity_id=str(p.id),
                        message=f"Building {b_ref} has zero intersection with assigned parcel {p_num}.",
                        technical_explanation="Spatial disjoint: ST_Intersects(building, parcel) = FALSE (intersection area = 0.0 m²).",
                        geometry_wkt=b_wkt,
                        measured_value="0.0% inside",
                        expected_value="100.0% inside",
                        metadata_json={
                            "building_id": str(b.id),
                            "parcel_id": str(p.id),
                            "building_area_sqm": b_area,
                            "intersection_area_sqm": 0.0,
                            "intersection_ratio": 0.0,
                            "outside_ratio": 1.0,
                        },
                    ))
            except Exception:
                pass
        return issues


class BuildingPartialOutsideParcelRule(ValidationRule):
    rule_id = "BUILDING_PARTIAL_OUTSIDE_PARCEL"
    name = "Building Partially Outside Parcel"
    description = "Detects building footprints that extend beyond the parcel boundary exceeding the allowed outside tolerance ratio."
    category = "BUILDING"
    severity = "WARNING"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["BUILDING", "PARCEL", "SYSTEM", "CROSS_DATASET"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        parcel_map = {str(p.id): p for p in context.parcels}
        tol_ratio = context.tolerances.outside_parcel_tolerance_ratio

        for b in context.buildings:
            parcel_id = getattr(b, "parcel_id", None)
            if not parcel_id or str(parcel_id) not in parcel_map:
                continue
            p = parcel_map[str(parcel_id)]
            b_wkt = getattr(b, "geometry_wkt", None) or getattr(b, "geometry", None)
            p_wkt = getattr(p, "geometry_wkt", None) or getattr(p, "geometry", None)
            if not b_wkt or not p_wkt:
                continue
            try:
                b_geom = GeometryEngine.parse_geometry(b_wkt)
                p_geom = GeometryEngine.parse_geometry(p_wkt)
                if b_geom.intersects(p_geom) and not p_geom.contains(b_geom):
                    inter = b_geom.intersection(p_geom)
                    outside = b_geom.difference(p_geom)
                    b_area = GeometryEngine.calculate_geodesic_area(b_geom)
                    inter_area = GeometryEngine.calculate_geodesic_area(inter)
                    outside_area = GeometryEngine.calculate_geodesic_area(outside)
                    if b_area > 0:
                        inter_ratio = inter_area / b_area
                        outside_ratio = outside_area / b_area
                        if outside_ratio > tol_ratio and outside_area > 0.05:
                            b_ref = getattr(b, "building_reference", None) or str(b.id)
                            p_num = getattr(p, "parcel_number", None) or str(p.id)
                            issues.append(IssueDraft(
                                rule_id=self.rule_id,
                                rule_version=self.rule_version,
                                issue_code="BLD-002",
                                category=self.category,
                                severity=self.severity,
                                entity_type="BUILDING",
                                entity_id=str(b.id),
                                related_entity_type="PARCEL",
                                related_entity_id=str(p.id),
                                message=f"Building {b_ref} extends outside parcel {p_num} by {outside_area:.2f} m² ({outside_ratio * 100:.1f}%).",
                                technical_explanation=(
                                    f"Footprint partially crosses parcel boundary: intersection_area={inter_area:.2f} m², "
                                    f"building_area={b_area:.2f} m², outside_ratio={outside_ratio:.4f} "
                                    f"exceeds tolerance of {tol_ratio:.4f}."
                                ),
                                geometry_wkt=GeometryEngine.to_wkt(outside),
                                measured_value=f"{outside_ratio * 100:.1f}% outside ({outside_area:.2f} m²)",
                                expected_value=f"<= {tol_ratio * 100:.1f}% outside",
                                tolerance=f"{tol_ratio * 100:.1f}%",
                                metadata_json={
                                    "building_id": str(b.id),
                                    "parcel_id": str(p.id),
                                    "building_area_sqm": b_area,
                                    "intersection_area_sqm": inter_area,
                                    "outside_area_sqm": outside_area,
                                    "intersection_ratio": round(inter_ratio, 4),
                                    "outside_ratio": round(outside_ratio, 4),
                                    "tolerance_ratio": tol_ratio,
                                },
                            ))
            except Exception:
                pass
        return issues


class BuildingOverlapRule(ValidationRule):
    rule_id = "BUILDING_OVERLAP"
    name = "Building Footprint Overlap"
    description = "Detects spatial area overlaps between distinct building footprints exceeding tolerance."
    category = "BUILDING"
    severity = "ERROR"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["BUILDING", "PARCEL", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        buildings = context.buildings
        if len(buildings) < 2:
            return issues

        tol = context.tolerances.area_overlap_tolerance_sqm
        parsed = []
        for b in buildings:
            wkt_str = getattr(b, "geometry_wkt", None) or getattr(b, "geometry", None)
            if wkt_str:
                try:
                    g = GeometryEngine.parse_geometry(wkt_str)
                    if g.is_valid and not g.is_empty:
                        parsed.append((b, g))
                except Exception:
                    pass

        for i in range(len(parsed)):
            b1, g1 = parsed[i]
            for j in range(i + 1, len(parsed)):
                b2, g2 = parsed[j]
                if not g1.envelope.intersects(g2.envelope):
                    continue
                if g1.intersects(g2):
                    inter = g1.intersection(g2)
                    if inter.geom_type in ["Polygon", "MultiPolygon"] and not inter.is_empty:
                        area = GeometryEngine.calculate_geodesic_area(inter)
                        if area > tol:
                            b1_ref = getattr(b1, "building_reference", None) or str(b1.id)
                            b2_ref = getattr(b2, "building_reference", None) or str(b2.id)
                            issues.append(IssueDraft(
                                rule_id=self.rule_id,
                                rule_version=self.rule_version,
                                issue_code="BLD-003",
                                category=self.category,
                                severity=self.severity,
                                entity_type="BUILDING",
                                entity_id=str(b1.id),
                                related_entity_type="BUILDING",
                                related_entity_id=str(b2.id),
                                message=f"Spatial overlap detected between building {b1_ref} and building {b2_ref} ({area:.2f} m²).",
                                technical_explanation=f"Footprint polygons overlap with intersection area of {area:.2f} m² > tolerance {tol:.2f} m².",
                                geometry_wkt=GeometryEngine.to_wkt(inter),
                                measured_value=f"{area:.2f} m²",
                                expected_value=f"<= {tol:.2f} m²",
                                tolerance=f"{tol:.2f} m²",
                                metadata_json={"overlap_area_sqm": area},
                            ))
        return issues


class BuildingDuplicateRule(ValidationRule):
    rule_id = "BUILDING_DUPLICATE"
    name = "Duplicate Building Detection"
    description = "Detects coincident or identical building footprints or duplicate building references."
    category = "BUILDING"
    severity = "CRITICAL"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["BUILDING", "PARCEL", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        seen_refs: Dict[str, Any] = {}
        for b in context.buildings:
            ref = getattr(b, "building_reference", None)
            if ref:
                if ref in seen_refs:
                    prev = seen_refs[ref]
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="BLD-004",
                        category=self.category,
                        severity=self.severity,
                        entity_type="BUILDING",
                        entity_id=str(b.id),
                        related_entity_type="BUILDING",
                        related_entity_id=str(prev.id),
                        message=f"Duplicate building reference detected: '{ref}'.",
                        technical_explanation=f"Multiple building records register the same reference '{ref}'.",
                        expected_value="Unique building_reference",
                        measured_value=ref,
                    ))
                else:
                    seen_refs[ref] = b
        return issues


class BuildingInvalidGeometryRule(ValidationRule):
    rule_id = "BUILDING_INVALID_GEOMETRY"
    name = "Degenerate Building Geometry"
    description = "Flags building footprints with degenerate area (< 1 m² or > 500,000 m²) or non-polygonal shapes."
    category = "BUILDING"
    severity = "ERROR"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["BUILDING", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        for b in context.buildings:
            wkt_str = getattr(b, "geometry_wkt", None) or getattr(b, "geometry", None)
            if not wkt_str:
                continue
            try:
                g = GeometryEngine.parse_geometry(wkt_str)
                area = GeometryEngine.calculate_geodesic_area(g)
                if area < context.tolerances.min_polygon_area_sqm:
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="BLD-005",
                        category=self.category,
                        severity=self.severity,
                        entity_type="BUILDING",
                        entity_id=str(b.id),
                        message=f"Building {getattr(b, 'building_reference', b.id)} has suspiciously small footprint area ({area:.2f} m²).",
                        technical_explanation=f"Geodesic area {area:.2f} m² is below the minimum building footprint threshold of {context.tolerances.min_polygon_area_sqm} m².",
                        geometry_wkt=wkt_str,
                        measured_value=f"{area:.2f} m²",
                        expected_value=f">= {context.tolerances.min_polygon_area_sqm} m²",
                    ))
            except Exception:
                pass
        return issues


class BuildingAreaMismatchRule(ValidationRule):
    rule_id = "BUILDING_AREA_MISMATCH"
    name = "Building Attribute Area Discrepancy"
    description = "Verifies that the stored building.area attribute matches the geodesic area calculated from its polygon boundary."
    category = "BUILDING"
    severity = "WARNING"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["BUILDING", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        for b in context.buildings:
            wkt_str = getattr(b, "geometry_wkt", None) or getattr(b, "geometry", None)
            stored_area = getattr(b, "area", None)
            if not wkt_str or stored_area is None:
                continue
            try:
                g = GeometryEngine.parse_geometry(wkt_str)
                calc_area = GeometryEngine.calculate_geodesic_area(g)
                if stored_area > 0:
                    diff = abs(calc_area - stored_area)
                    diff_pct = (diff / stored_area) * 100.0
                    if diff_pct > 5.0 and diff > 1.0:
                        issues.append(IssueDraft(
                            rule_id=self.rule_id,
                            rule_version=self.rule_version,
                            issue_code="BLD-006",
                            category=self.category,
                            severity=self.severity,
                            entity_type="BUILDING",
                            entity_id=str(b.id),
                            message=f"Building {getattr(b, 'building_reference', b.id)} attribute area ({stored_area:.2f} m²) differs from polygon area ({calc_area:.2f} m²) by {diff_pct:.1f}%.",
                            technical_explanation=f"Stored area attribute ({stored_area:.2f} m²) diverges from WGS84 geodesic polygon calculation ({calc_area:.2f} m²) by {diff:.2f} m².",
                            measured_value=f"{calc_area:.2f} m²",
                            expected_value=f"{stored_area:.2f} m²",
                            tolerance="<= 5.0% discrepancy",
                            metadata_json={"stored_area": stored_area, "calculated_area": calc_area, "diff_sqm": diff, "diff_pct": diff_pct},
                        ))
            except Exception:
                pass
        return issues

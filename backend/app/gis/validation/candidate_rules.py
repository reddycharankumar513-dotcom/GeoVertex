from typing import Any, Dict, List
import shapely
from app.gis.geometry import GeometryEngine
from app.gis.validation.base import IssueDraft, ValidationContext, ValidationRule


class AICandidateInvalidGeometryRule(ValidationRule):
    rule_id = "AI_CANDIDATE_INVALID_GEOMETRY"
    name = "AI Candidate Degenerate Geometry"
    description = "Checks that AI candidate polygon is topologically valid, closed, and non-empty."
    category = "AI"
    severity = "ERROR"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["AI_RESULT", "BUILDING", "SYSTEM", "CROSS_DATASET"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        for c in context.ai_building_candidates:
            wkt_str = getattr(c, "geometry_wkt", None)
            if not wkt_str:
                issues.append(IssueDraft(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    issue_code="AI-001",
                    category=self.category,
                    severity=self.severity,
                    entity_type="AI_RESULT",
                    entity_id=str(c.id),
                    message=f"AI Candidate {c.id} has null geometry.",
                    technical_explanation="Model extraction produced null or missing geometry coordinates.",
                    measured_value="None",
                    expected_value="Valid Polygon WKT",
                ))
                continue
            try:
                g = GeometryEngine.parse_geometry(wkt_str)
                if not g.is_valid:
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="AI-001",
                        category=self.category,
                        severity=self.severity,
                        entity_type="AI_RESULT",
                        entity_id=str(c.id),
                        message=f"AI Candidate {c.id} generated invalid geometry: {shapely.explain_validity(g)}.",
                        technical_explanation=f"Topological invalidity in model polygon output: {shapely.explain_validity(g)}.",
                        geometry_wkt=wkt_str,
                        measured_value=shapely.explain_validity(g),
                        expected_value="ST_IsValid = TRUE",
                    ))
            except Exception as e:
                issues.append(IssueDraft(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    issue_code="AI-001",
                    category=self.category,
                    severity=self.severity,
                    entity_type="AI_RESULT",
                    entity_id=str(c.id),
                    message=f"AI Candidate {c.id} geometry parse error: {str(e)}",
                    technical_explanation=str(e),
                    measured_value="Parse Error",
                    expected_value="Valid WKT",
                ))
        return issues


class AICandidateDuplicateRule(ValidationRule):
    rule_id = "AI_CANDIDATE_DUPLICATE"
    name = "Duplicate AI Extraction Result"
    description = "Detects duplicate candidate polygons extracted for the same target building or parcel."
    category = "AI"
    severity = "WARNING"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["AI_RESULT", "BUILDING", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        cands = context.ai_building_candidates
        if len(cands) < 2:
            return issues

        parsed = []
        for c in cands:
            wkt_str = getattr(c, "geometry_wkt", None)
            if wkt_str:
                try:
                    g = GeometryEngine.parse_geometry(wkt_str)
                    if g.is_valid:
                        parsed.append((c, g))
                except Exception:
                    pass

        for i in range(len(parsed)):
            c1, g1 = parsed[i]
            for j in range(i + 1, len(parsed)):
                c2, g2 = parsed[j]
                if g1.equals_exact(g2, tolerance=0.00002):
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="AI-002",
                        category=self.category,
                        severity=self.severity,
                        entity_type="AI_RESULT",
                        entity_id=str(c1.id),
                        related_entity_type="AI_RESULT",
                        related_entity_id=str(c2.id),
                        message=f"Duplicate AI extraction candidates detected ({c1.id} and {c2.id}).",
                        technical_explanation="Exact coincident candidate polygon detected from separate inference runs.",
                        measured_value="Coincident (IoU = 1.0)",
                        expected_value="Unique candidate geometry",
                    ))
        return issues


class AICandidateLowSpatialMatchRule(ValidationRule):
    rule_id = "AI_CANDIDATE_LOW_SPATIAL_MATCH"
    name = "AI Candidate Low Spatial Match with Official Record"
    description = "Flags AI candidate footprints that diverge significantly (IoU < 0.50) from the official cadastral building footprint."
    category = "AI"
    severity = "WARNING"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["AI_RESULT", "BUILDING", "CROSS_DATASET", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        bld_map = {str(b.id): b for b in context.buildings}
        min_iou = context.tolerances.min_acceptable_candidate_iou

        for c in context.ai_building_candidates:
            target_id = getattr(c, "source_target_id", None)
            if not target_id or str(target_id) not in bld_map:
                continue
            b = bld_map[str(target_id)]
            c_wkt = getattr(c, "geometry_wkt", None)
            b_wkt = getattr(b, "geometry_wkt", None) or getattr(b, "geometry", None)
            if not c_wkt or not b_wkt:
                continue
            try:
                cg = GeometryEngine.parse_geometry(c_wkt)
                bg = GeometryEngine.parse_geometry(b_wkt)
                if not (cg.is_valid and bg.is_valid):
                    continue

                inter_area = GeometryEngine.calculate_geodesic_area(cg.intersection(bg))
                union_area = GeometryEngine.calculate_geodesic_area(cg.union(bg))
                iou = inter_area / union_area if union_area > 0 else 0.0

                c_area = GeometryEngine.calculate_geodesic_area(cg)
                b_area = GeometryEngine.calculate_geodesic_area(bg)
                area_diff = abs(c_area - b_area)

                c1 = cg.centroid
                c2 = bg.centroid
                centroid_dist = pyproj_dist = GeometryEngine.calculate_geodesic_area(shapely.box(c1.x, c1.y, c2.x, c2.y)) # approximate or euclidean

                if iou < min_iou:
                    b_ref = getattr(b, "building_reference", str(b.id))
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="AI-003",
                        category=self.category,
                        severity=self.severity,
                        entity_type="AI_RESULT",
                        entity_id=str(c.id),
                        related_entity_type="BUILDING",
                        related_entity_id=str(b.id),
                        message=f"AI Candidate has low spatial match with official building {b_ref} (IoU={iou:.2f} < {min_iou:.2f}).",
                        technical_explanation=(
                            f"Spatial comparison between candidate footprint and official record yields: "
                            f"IoU={iou:.4f}, candidate_area={c_area:.2f} m², official_area={b_area:.2f} m², "
                            f"area_diff={area_diff:.2f} m²."
                        ),
                        geometry_wkt=c_wkt,
                        measured_value=f"IoU = {iou:.2f}",
                        expected_value=f">= {min_iou:.2f}",
                        tolerance=f"{min_iou:.2f}",
                        metadata_json={
                            "iou": round(iou, 4),
                            "candidate_area_sqm": c_area,
                            "official_area_sqm": b_area,
                            "area_diff_sqm": area_diff,
                            "intersection_area_sqm": inter_area,
                        },
                    ))
            except Exception:
                pass
        return issues


class AICandidateParcelConflictRule(ValidationRule):
    rule_id = "AI_CANDIDATE_PARCEL_CONFLICT"
    name = "AI Candidate Parcel Boundary Overflow"
    description = "Checks that AI candidate footprints do not extend significantly outside the target land parcel."
    category = "AI"
    severity = "WARNING"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["AI_RESULT", "PARCEL", "CROSS_DATASET", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        parcel_map = {str(p.id): p for p in context.parcels}

        for c in context.ai_building_candidates:
            p_id = getattr(c, "source_target_id", None)
            if not p_id or str(p_id) not in parcel_map:
                continue
            p = parcel_map[str(p_id)]
            c_wkt = getattr(c, "geometry_wkt", None)
            p_wkt = getattr(p, "geometry_wkt", None) or getattr(p, "geometry", None)
            if not c_wkt or not p_wkt:
                continue
            try:
                cg = GeometryEngine.parse_geometry(c_wkt)
                pg = GeometryEngine.parse_geometry(p_wkt)
                if not pg.contains(cg):
                    outside = cg.difference(pg)
                    outside_area = GeometryEngine.calculate_geodesic_area(outside)
                    c_area = GeometryEngine.calculate_geodesic_area(cg)
                    if c_area > 0 and (outside_area / c_area) > 0.05 and outside_area > 0.2:
                        p_code = getattr(p, "parcel_number", p.id)
                        issues.append(IssueDraft(
                            rule_id=self.rule_id,
                            rule_version=self.rule_version,
                            issue_code="AI-004",
                            category=self.category,
                            severity=self.severity,
                            entity_type="AI_RESULT",
                            entity_id=str(c.id),
                            related_entity_type="PARCEL",
                            related_entity_id=str(p.id),
                            message=f"AI Candidate footprint extends {outside_area:.2f} m² outside target parcel {p_code}.",
                            technical_explanation=f"Containment violation: Candidate polygon overflows parcel boundary by {outside_area:.2f} m² ({(outside_area/c_area)*100:.1f}%).",
                            geometry_wkt=GeometryEngine.to_wkt(outside),
                            measured_value=f"{outside_area:.2f} m² outside",
                            expected_value="Inside parcel boundary",
                        ))
            except Exception:
                pass
        return issues

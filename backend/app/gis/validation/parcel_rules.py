from typing import Any, Dict, List
import shapely
from app.gis.geometry import GeometryEngine
from app.gis.validation.base import IssueDraft, ValidationContext, ValidationRule


class ParcelOverlapRule(ValidationRule):
    rule_id = "PARCEL_OVERLAP"
    name = "Parcel Area Overlap"
    description = "Detects 2D spatial area overlaps between adjacent land parcels exceeding the configured tolerance threshold."
    category = "PARCEL"
    severity = "ERROR"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["PARCEL", "JURISDICTION", "SYSTEM", "CROSS_DATASET"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        parcels = context.parcels
        if len(parcels) < 2:
            return issues

        tol = context.tolerances.area_overlap_tolerance_sqm
        parsed_parcels = []
        for p in parcels:
            wkt_str = getattr(p, "geometry_wkt", None) or getattr(p, "geometry", None)
            if not wkt_str:
                continue
            try:
                geom = GeometryEngine.parse_geometry(wkt_str)
                if geom.is_valid and not geom.is_empty:
                    parsed_parcels.append((p, geom))
            except Exception:
                continue

        # Pairwise comparison
        for i in range(len(parsed_parcels)):
            p1, g1 = parsed_parcels[i]
            for j in range(i + 1, len(parsed_parcels)):
                p2, g2 = parsed_parcels[j]

                # Bounding box quick reject
                if not g1.envelope.intersects(g2.envelope):
                    continue

                if g1.intersects(g2):
                    inter = g1.intersection(g2)
                    # Check dimension: an intersection of dimension 2 (Polygon) is an area overlap.
                    # Touches along boundary edges (LineString/Point) are standard valid cadastral coterminous boundaries!
                    if inter.geom_type in ["Polygon", "MultiPolygon"] and not inter.is_empty:
                        overlap_area = GeometryEngine.calculate_geodesic_area(inter)
                        if overlap_area > tol:
                            p1_code = getattr(p1, "parcel_number", None) or getattr(p1, "parcel_code", str(p1.id))
                            p2_code = getattr(p2, "parcel_number", None) or getattr(p2, "parcel_code", str(p2.id))
                            issues.append(IssueDraft(
                                rule_id=self.rule_id,
                                rule_version=self.rule_version,
                                issue_code="PCL-001",
                                category=self.category,
                                severity=self.severity,
                                entity_type="PARCEL",
                                entity_id=str(p1.id),
                                related_entity_type="PARCEL",
                                related_entity_id=str(p2.id),
                                message=f"Spatial overlap detected between parcel {p1_code} and parcel {p2_code} ({overlap_area:.2f} m²).",
                                technical_explanation=f"Polygonal intersection ST_Intersection(p1, p2) has geodesic area of {overlap_area:.2f} m², which exceeds the allowed tolerance of {tol:.2f} m².",
                                geometry_wkt=GeometryEngine.to_wkt(inter),
                                measured_value=f"{overlap_area:.2f} m²",
                                expected_value=f"<= {tol:.2f} m²",
                                tolerance=f"{tol:.2f} m²",
                                metadata_json={
                                    "parcel_1_id": str(p1.id),
                                    "parcel_2_id": str(p2.id),
                                    "parcel_1_code": p1_code,
                                    "parcel_2_code": p2_code,
                                    "overlap_area_sqm": overlap_area,
                                    "intersection_geom_type": inter.geom_type,
                                },
                            ))
        return issues


class ParcelDuplicateRule(ValidationRule):
    rule_id = "PARCEL_DUPLICATE"
    name = "Duplicate Parcel Detection"
    description = "Detects exact or near-identical coincident boundaries or duplicate parcel identifiers."
    category = "PARCEL"
    severity = "CRITICAL"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["PARCEL", "JURISDICTION", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        parcels = context.parcels
        seen_codes: Dict[str, Any] = {}

        for p in parcels:
            code = getattr(p, "parcel_number", None) or getattr(p, "parcel_code", None)
            if code:
                if code in seen_codes:
                    prev = seen_codes[code]
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="PCL-002",
                        category=self.category,
                        severity=self.severity,
                        entity_type="PARCEL",
                        entity_id=str(p.id),
                        related_entity_type="PARCEL",
                        related_entity_id=str(prev.id),
                        message=f"Duplicate parcel identifier detected: '{code}'.",
                        technical_explanation=f"Multiple parcel records share the identical parcel identifier '{code}'.",
                        expected_value="Unique parcel number",
                        measured_value=code,
                    ))
                else:
                    seen_codes[code] = p

        # Check geometric duplicates (IoU > 0.99)
        parsed = []
        for p in parcels:
            wkt_str = getattr(p, "geometry_wkt", None) or getattr(p, "geometry", None)
            if wkt_str:
                try:
                    g = GeometryEngine.parse_geometry(wkt_str)
                    if g.is_valid and not g.is_empty:
                        parsed.append((p, g))
                except Exception:
                    pass

        for i in range(len(parsed)):
            p1, g1 = parsed[i]
            for j in range(i + 1, len(parsed)):
                p2, g2 = parsed[j]
                if g1.equals_exact(g2, tolerance=0.00001):
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="PCL-002",
                        category=self.category,
                        severity=self.severity,
                        entity_type="PARCEL",
                        entity_id=str(p1.id),
                        related_entity_type="PARCEL",
                        related_entity_id=str(p2.id),
                        message=f"Exact coincident geometry detected between parcel {p1.id} and parcel {p2.id}.",
                        technical_explanation="Both parcels possess geometrically identical vertex boundaries (IoU = 1.0).",
                        geometry_wkt=GeometryEngine.to_wkt(g1),
                        expected_value="Independent geometries",
                        measured_value="Coincident boundaries (IoU = 1.0)",
                    ))
        return issues


class ParcelOutsideJurisdictionRule(ValidationRule):
    rule_id = "PARCEL_OUTSIDE_JURISDICTION"
    name = "Parcel Outside Administrative Jurisdiction"
    description = "Checks that the parcel geometry is fully contained inside its registered administrative jurisdiction boundary."
    category = "PARCEL"
    severity = "ERROR"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["PARCEL", "JURISDICTION", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        jurisdiction_map = {str(j.id): j for j in context.jurisdictions}
        for p in context.parcels:
            jur_id = getattr(p, "jurisdiction_id", None)
            if not jur_id or str(jur_id) not in jurisdiction_map:
                continue
            jur = jurisdiction_map[str(jur_id)]
            jur_wkt = getattr(jur, "boundary_wkt", None) or getattr(jur, "boundary", None)
            p_wkt = getattr(p, "geometry_wkt", None) or getattr(p, "geometry", None)
            if not jur_wkt or not p_wkt:
                continue
            try:
                j_geom = GeometryEngine.parse_geometry(jur_wkt)
                p_geom = GeometryEngine.parse_geometry(p_wkt)
                if not j_geom.contains(p_geom):
                    outside = p_geom.difference(j_geom)
                    outside_area = GeometryEngine.calculate_geodesic_area(outside)
                    if outside_area > 0.1:
                        issues.append(IssueDraft(
                            rule_id=self.rule_id,
                            rule_version=self.rule_version,
                            issue_code="PCL-003",
                            category=self.category,
                            severity=self.severity,
                            entity_type="PARCEL",
                            entity_id=str(p.id),
                            related_entity_type="JURISDICTION",
                            related_entity_id=str(jur.id),
                            message=f"Parcel {p.parcel_number or p.id} extends outside jurisdiction {jur.name} by {outside_area:.2f} m².",
                            technical_explanation=f"ST_Contains(jurisdiction, parcel) is false. Outside area: {outside_area:.2f} m².",
                            geometry_wkt=GeometryEngine.to_wkt(outside),
                            measured_value=f"{outside_area:.2f} m² outside",
                            expected_value="100% containment",
                        ))
            except Exception:
                pass
        return issues


class ParcelMissingPropertyRule(ValidationRule):
    rule_id = "PARCEL_MISSING_PROPERTY"
    name = "Parcel Without Linked Property"
    description = "Flags active parcels that have no registered property or ownership registry link."
    category = "PARCEL"
    severity = "WARNING"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["PARCEL", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        for p in context.parcels:
            props = p.__dict__.get("properties") if hasattr(p, "__dict__") else getattr(p, "properties", None)
            if props is not None and len(props) == 0:
                p_code = getattr(p, "parcel_number", None) or str(p.id)
                issues.append(IssueDraft(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    issue_code="PCL-004",
                    category=self.category,
                    severity=self.severity,
                    entity_type="PARCEL",
                    entity_id=str(p.id),
                    message=f"Parcel {p_code} has no associated Property record.",
                    technical_explanation="Active cadastral parcel exists without any associated legal Property entity in the property registry.",
                    expected_value=">= 1 Property record",
                    measured_value="0 Properties",
                ))
        return issues

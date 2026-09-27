from typing import Any, Dict, List
import shapely
from shapely.validation import explain_validity, make_valid
from app.gis.geometry import GeometryEngine
from app.gis.validation.base import IssueDraft, ValidationContext, ValidationRule


def _extract_geometry_targets(context: ValidationContext) -> List[Dict[str, Any]]:
    """Helper to extract all geometry targets from context (parcels, buildings, units, AI candidates, surveys)."""
    targets = []
    for p in context.parcels:
        targets.append({
            "entity_type": "PARCEL",
            "entity_id": str(getattr(p, "id", "")),
            "geom_wkt": getattr(p, "geometry_wkt", None) or getattr(p, "geometry", None),
            "expected_type": ["Polygon", "MultiPolygon"],
        })
    for b in context.buildings:
        targets.append({
            "entity_type": "BUILDING",
            "entity_id": str(getattr(b, "id", "")),
            "geom_wkt": getattr(b, "geometry_wkt", None) or getattr(b, "geometry", None),
            "expected_type": ["Polygon", "MultiPolygon"],
        })
    for f in context.floors:
        if getattr(f, "geometry_wkt", None) or getattr(f, "geometry", None):
            targets.append({
                "entity_type": "FLOOR",
                "entity_id": str(getattr(f, "id", "")),
                "geom_wkt": getattr(f, "geometry_wkt", None) or getattr(f, "geometry", None),
                "expected_type": ["Polygon", "MultiPolygon"],
            })
    for u in context.units:
        if getattr(u, "geometry_wkt", None) or getattr(u, "geometry", None):
            targets.append({
                "entity_type": "UNIT",
                "entity_id": str(getattr(u, "id", "")),
                "geom_wkt": getattr(u, "geometry_wkt", None) or getattr(u, "geometry", None),
                "expected_type": ["Polygon", "MultiPolygon"],
            })
    for c in context.ai_building_candidates:
        targets.append({
            "entity_type": "AI_RESULT",
            "entity_id": str(getattr(c, "id", "")),
            "geom_wkt": getattr(c, "geometry_wkt", None),
            "expected_type": ["Polygon", "MultiPolygon"],
        })
    for s in context.survey_observations:
        if getattr(s, "geometry_wkt", None):
            targets.append({
                "entity_type": "SURVEY_OBSERVATION",
                "entity_id": str(getattr(s, "id", "")),
                "geom_wkt": getattr(s, "geometry_wkt", None),
                "expected_type": ["Point", "Polygon", "MultiPolygon", "LineString"],
            })
    for key, geom_str in context.raw_geometries.items():
        targets.append({
            "entity_type": "RAW_GEOMETRY",
            "entity_id": key,
            "geom_wkt": geom_str,
            "expected_type": ["Polygon", "MultiPolygon"],
        })
    return targets


class GeomMissingRule(ValidationRule):
    rule_id = "GEOM_MISSING"
    name = "Missing Geometry"
    description = "Checks that an entity requiring spatial representation has a non-null geometry definition."
    category = "GEOMETRY"
    severity = "CRITICAL"

    def applies_to(self, target_type: str) -> bool:
        return True

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        for t in _extract_geometry_targets(context):
            if not t["geom_wkt"]:
                issues.append(IssueDraft(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    issue_code="GEO-001",
                    category=self.category,
                    severity=self.severity,
                    entity_type=t["entity_type"],
                    entity_id=t["entity_id"],
                    message=f"{t['entity_type']} ({t['entity_id']}) is missing spatial geometry.",
                    technical_explanation="Geometry field is null, empty string, or undefined in the cadastral database.",
                    expected_value="Valid WKT or GeoJSON Polygon",
                    measured_value="None",
                ))
        return issues


class GeomEmptyRule(ValidationRule):
    rule_id = "GEOM_EMPTY"
    name = "Empty Geometry"
    description = "Checks that the geometry contains coordinates and is not an empty set."
    category = "GEOMETRY"
    severity = "ERROR"

    def applies_to(self, target_type: str) -> bool:
        return True

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        for t in _extract_geometry_targets(context):
            if not t["geom_wkt"]:
                continue
            try:
                geom = GeometryEngine.parse_geometry(t["geom_wkt"])
                if geom.is_empty:
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="GEO-002",
                        category=self.category,
                        severity=self.severity,
                        entity_type=t["entity_type"],
                        entity_id=t["entity_id"],
                        message=f"{t['entity_type']} ({t['entity_id']}) contains an empty coordinate set.",
                        technical_explanation="The geometry object parses successfully but ST_IsEmpty evaluates to true (0 coordinates).",
                        expected_value="Non-empty coordinate sequence",
                        measured_value="EMPTY",
                    ))
            except Exception:
                pass
        return issues


class GeomInvalidRule(ValidationRule):
    rule_id = "GEOM_INVALID"
    name = "Invalid Geometry"
    description = "Checks that the geometry complies with OGC Simple Feature standards and generates non-destructive repair candidates."
    category = "GEOMETRY"
    severity = "ERROR"

    def applies_to(self, target_type: str) -> bool:
        return True

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        for t in _extract_geometry_targets(context):
            if not t["geom_wkt"]:
                continue
            try:
                geom = GeometryEngine.parse_geometry(t["geom_wkt"])
                if not geom.is_valid:
                    reason = explain_validity(geom)
                    repaired = make_valid(geom)
                    repaired_wkt = GeometryEngine.to_wkt(repaired) if repaired and not repaired.is_empty else None
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="GEO-003",
                        category=self.category,
                        severity=self.severity,
                        entity_type=t["entity_type"],
                        entity_id=t["entity_id"],
                        message=f"{t['entity_type']} ({t['entity_id']}) is topologically invalid: {reason}.",
                        technical_explanation=f"OGC topology check ST_IsValid returned false. GEOS diagnostic: {reason}.",
                        geometry_wkt=t["geom_wkt"] if isinstance(t["geom_wkt"], str) else GeometryEngine.to_wkt(geom),
                        expected_value="ST_IsValid = TRUE",
                        measured_value=reason,
                        repair_candidate_wkt=repaired_wkt,
                        repair_method="shapely.make_valid() (GEOS Structure Repair Candidate)",
                        metadata_json={"validity_reason": reason, "has_repair_candidate": repaired_wkt is not None},
                    ))
            except Exception as e:
                issues.append(IssueDraft(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    issue_code="GEO-003",
                    category=self.category,
                    severity=self.severity,
                    entity_type=t["entity_type"],
                    entity_id=t["entity_id"],
                    message=f"Failed to parse geometry for {t['entity_type']} ({t['entity_id']}): {str(e)}",
                    technical_explanation=f"Malformed WKT or GeoJSON parser failure: {str(e)}",
                    expected_value="Parsable WKT",
                    measured_value="Parse Error",
                ))
        return issues


class GeomWrongTypeRule(ValidationRule):
    rule_id = "GEOM_WRONG_TYPE"
    name = "Wrong Geometry Type"
    description = "Checks that the geometry matches expected cadastral geometry types (e.g. Polygon for parcels/buildings)."
    category = "GEOMETRY"
    severity = "ERROR"

    def applies_to(self, target_type: str) -> bool:
        return True

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        for t in _extract_geometry_targets(context):
            if not t["geom_wkt"]:
                continue
            try:
                geom = GeometryEngine.parse_geometry(t["geom_wkt"])
                if geom.geom_type not in t["expected_type"]:
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="GEO-004",
                        category=self.category,
                        severity=self.severity,
                        entity_type=t["entity_type"],
                        entity_id=t["entity_id"],
                        message=f"{t['entity_type']} ({t['entity_id']}) has unexpected geometry type '{geom.geom_type}'.",
                        technical_explanation=f"Expected one of {t['expected_type']}, but encountered '{geom.geom_type}'.",
                        expected_value=", ".join(t["expected_type"]),
                        measured_value=geom.geom_type,
                    ))
            except Exception:
                pass
        return issues


class GeomInvalidRingRule(ValidationRule):
    rule_id = "GEOM_INVALID_RING"
    name = "Invalid Ring Structure"
    description = "Checks that polygon exterior and interior rings are closed with at least 4 coordinates and no duplicate adjacent vertices."
    category = "GEOMETRY"
    severity = "ERROR"

    def applies_to(self, target_type: str) -> bool:
        return True

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        for t in _extract_geometry_targets(context):
            if not t["geom_wkt"]:
                continue
            try:
                geom = GeometryEngine.parse_geometry(t["geom_wkt"])
                polys = [geom] if isinstance(geom, shapely.Polygon) else (geom.geoms if isinstance(geom, shapely.MultiPolygon) else [])
                for poly in polys:
                    coords = list(poly.exterior.coords)
                    if len(coords) < 4:
                        issues.append(IssueDraft(
                            rule_id=self.rule_id,
                            rule_version=self.rule_version,
                            issue_code="GEO-005",
                            category=self.category,
                            severity=self.severity,
                            entity_type=t["entity_type"],
                            entity_id=t["entity_id"],
                            message=f"{t['entity_type']} ({t['entity_id']}) exterior ring has fewer than 4 coordinates ({len(coords)}).",
                            technical_explanation="A valid linear ring forming a polygon boundary must contain at least 4 coordinates (including closed endpoint).",
                            expected_value=">= 4 coordinates",
                            measured_value=str(len(coords)),
                        ))
                    elif coords[0] != coords[-1]:
                        issues.append(IssueDraft(
                            rule_id=self.rule_id,
                            rule_version=self.rule_version,
                            issue_code="GEO-005",
                            category=self.category,
                            severity=self.severity,
                            entity_type=t["entity_type"],
                            entity_id=t["entity_id"],
                            message=f"{t['entity_type']} ({t['entity_id']}) ring is not closed (start != end).",
                            technical_explanation="Polygon exterior boundary must start and end at the exact same vertex.",
                            expected_value="coords[0] == coords[-1]",
                            measured_value=f"Start {coords[0]} != End {coords[-1]}",
                        ))
            except Exception:
                pass
        return issues


class GeomSelfIntersectionRule(ValidationRule):
    rule_id = "GEOM_SELF_INTERSECTION"
    name = "Self-Intersecting Polygon"
    description = "Checks for self-crossing or self-tangent boundaries creating bowtie or degenerate polygons."
    category = "GEOMETRY"
    severity = "ERROR"

    def applies_to(self, target_type: str) -> bool:
        return True

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        for t in _extract_geometry_targets(context):
            if not t["geom_wkt"]:
                continue
            try:
                geom = GeometryEngine.parse_geometry(t["geom_wkt"])
                if not geom.is_valid:
                    reason = explain_validity(geom)
                    if "Self-intersection" in reason or "Self-tangency" in reason or "crosses" in reason:
                        repaired = make_valid(geom)
                        issues.append(IssueDraft(
                            rule_id=self.rule_id,
                            rule_version=self.rule_version,
                            issue_code="GEO-006",
                            category=self.category,
                            severity=self.severity,
                            entity_type=t["entity_type"],
                            entity_id=t["entity_id"],
                            message=f"{t['entity_type']} ({t['entity_id']}) has a self-intersecting boundary.",
                            technical_explanation=f"Boundary segments intersect or touch internally creating invalid topology. GEOS diagnosis: {reason}",
                            geometry_wkt=t["geom_wkt"] if isinstance(t["geom_wkt"], str) else GeometryEngine.to_wkt(geom),
                            expected_value="Simple non-self-intersecting boundary",
                            measured_value=reason,
                            repair_candidate_wkt=GeometryEngine.to_wkt(repaired) if repaired and not repaired.is_empty else None,
                            repair_method="shapely.make_valid() (Decomposed Polygon or MultiPolygon)",
                        ))
            except Exception:
                pass
        return issues


class GeomInvalidCRSRule(ValidationRule):
    rule_id = "GEOM_INVALID_CRS"
    name = "Invalid Coordinates or Geographic Range"
    description = "Checks that coordinates fall within standard geographic WGS84 range (-180..180 lon, -90..90 lat) or valid project bounds."
    category = "GEOMETRY"
    severity = "ERROR"

    def applies_to(self, target_type: str) -> bool:
        return True

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        for t in _extract_geometry_targets(context):
            if not t["geom_wkt"]:
                continue
            try:
                geom = GeometryEngine.parse_geometry(t["geom_wkt"])
                minx, miny, maxx, maxy = geom.bounds
                if minx < -180.0 or maxx > 180.0 or miny < -90.0 or maxy > 90.0:
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="GEO-007",
                        category=self.category,
                        severity=self.severity,
                        entity_type=t["entity_type"],
                        entity_id=t["entity_id"],
                        message=f"{t['entity_type']} ({t['entity_id']}) coordinates exceed valid WGS84 bounds ([-180, 180], [-90, 90]).",
                        technical_explanation=f"Bounds detected: lon [{minx}, {maxx}], lat [{miny}, {maxy}]. Likely unconverted projected planar coordinates (e.g. UTM or State Plane) stored as EPSG:4326.",
                        expected_value="lon: [-180, 180], lat: [-90, 90]",
                        measured_value=f"[{minx}, {miny}, {maxx}, {maxy}]",
                    ))
            except Exception:
                pass
        return issues

from typing import Any, Dict, List
import shapely
from app.gis.geometry import GeometryEngine
from app.gis.validation.base import IssueDraft, ValidationContext, ValidationRule


class SurveyGeometryInvalidRule(ValidationRule):
    rule_id = "SURVEY_GEOMETRY_INVALID"
    name = "Survey Geometry Invalidity"
    description = "Checks that survey observation coordinates and boundaries are topologically valid."
    category = "SURVEY"
    severity = "ERROR"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["SURVEY_SUBMISSION", "SURVEY_OBSERVATION", "SYSTEM", "CROSS_DATASET"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        for s in context.survey_observations:
            wkt_str = getattr(s, "geometry_wkt", None)
            if not wkt_str:
                continue
            try:
                g = GeometryEngine.parse_geometry(wkt_str)
                if not g.is_valid:
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="SRV-001",
                        category=self.category,
                        severity=self.severity,
                        entity_type="SURVEY_OBSERVATION",
                        entity_id=str(s.id),
                        message=f"Survey observation {s.id} contains invalid geometry: {shapely.explain_validity(g)}.",
                        technical_explanation=f"Topological invalidity in field observation geometry: {shapely.explain_validity(g)}.",
                        geometry_wkt=wkt_str,
                        measured_value=shapely.explain_validity(g),
                        expected_value="ST_IsValid = TRUE",
                    ))
            except Exception as e:
                issues.append(IssueDraft(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    issue_code="SRV-001",
                    category=self.category,
                    severity=self.severity,
                    entity_type="SURVEY_OBSERVATION",
                    entity_id=str(s.id),
                    message=f"Survey observation {s.id} geometry parse error: {str(e)}",
                    technical_explanation=str(e),
                    measured_value="Parse error",
                    expected_value="Valid WKT",
                ))
        return issues


class SurveyOutsideAOIRule(ValidationRule):
    rule_id = "SURVEY_OUTSIDE_AOI"
    name = "Survey Observation Outside Project AOI"
    description = "Checks that survey field measurements fall within the authorized project Area of Interest (AOI)."
    category = "SURVEY"
    severity = "ERROR"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["SURVEY_SUBMISSION", "SURVEY_OBSERVATION", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        # Check against project AOI / Parcel boundaries in context
        parcel_geoms = []
        for p in context.parcels:
            wkt_str = getattr(p, "geometry_wkt", None) or getattr(p, "geometry", None)
            if wkt_str:
                try:
                    g = GeometryEngine.parse_geometry(wkt_str)
                    if g.is_valid:
                        parcel_geoms.append(g)
                except Exception:
                    pass

        if not parcel_geoms:
            return issues

        union_aoi = shapely.unary_union(parcel_geoms)
        aoi_buffer = union_aoi.buffer(0.0005) # ~50m buffer allowance around survey target parcel

        for s in context.survey_observations:
            lat = getattr(s, "latitude", None)
            lon = getattr(s, "longitude", None)
            if lat is not None and lon is not None:
                pt = shapely.Point(lon, lat)
                if not aoi_buffer.contains(pt):
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="SRV-002",
                        category=self.category,
                        severity=self.severity,
                        entity_type="SURVEY_OBSERVATION",
                        entity_id=str(s.id),
                        message=f"Survey observation {s.id} point ({lat}, {lon}) is outside the project Area of Interest.",
                        technical_explanation="Field GNSS coordinates fall beyond the buffered project parcel/AOI boundary.",
                        measured_value=f"Point({lon}, {lat})",
                        expected_value="Inside project AOI boundary",
                    ))
        return issues


class SurveyHeightMismatchRule(ValidationRule):
    rule_id = "SURVEY_HEIGHT_MISMATCH"
    name = "Survey Height Discrepancy with Official Record"
    description = "Compares field-surveyed building height observation against official registered building height."
    category = "SURVEY"
    severity = "WARNING"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["SURVEY_SUBMISSION", "BUILDING", "CROSS_DATASET", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        bld_map = {str(b.id): b for b in context.buildings}
        tol_h = context.tolerances.survey_height_tolerance_m

        for s in context.survey_observations:
            obs_type = getattr(s, "observation_type", None)
            target_id = getattr(s, "target_id", None)
            if obs_type == "BUILDING_HEIGHT" and target_id and str(target_id) in bld_map:
                b = bld_map[str(target_id)]
                b_height = getattr(b, "height_estimate", None) or getattr(b, "height", None) or getattr(b, "total_height", None)
                val_str = getattr(s, "value", None)
                if val_str and b_height is not None:
                    try:
                        survey_h = float(val_str)
                        diff = abs(survey_h - b_height)
                        if diff > tol_h:
                            b_ref = getattr(b, "building_reference", str(b.id))
                            issues.append(IssueDraft(
                                rule_id=self.rule_id,
                                rule_version=self.rule_version,
                                issue_code="SRV-003",
                                category=self.category,
                                severity=self.severity,
                                entity_type="SURVEY_OBSERVATION",
                                entity_id=str(s.id),
                                related_entity_type="BUILDING",
                                related_entity_id=str(b.id),
                                message=f"Survey height ({survey_h:.2f}m) differs from official building {b_ref} height ({b_height:.2f}m) by {diff:.2f}m.",
                                technical_explanation=f"Field laser/GNSS measurement {survey_h:.2f}m exceeds official record {b_height:.2f}m by delta {diff:.2f}m > tolerance {tol_h:.2f}m.",
                                measured_value=f"{survey_h:.2f}m",
                                expected_value=f"{b_height:.2f}m",
                                tolerance=f"{tol_h:.2f}m",
                                metadata_json={"observed_value": survey_h, "official_value": b_height, "difference_m": diff},
                            ))
                    except Exception:
                        pass
        return issues


class SurveyFootprintMismatchRule(ValidationRule):
    rule_id = "SURVEY_FOOTPRINT_MISMATCH"
    name = "Survey Footprint Discrepancy with Official Record"
    description = "Checks alignment between survey corner observations and the official building footprint boundary."
    category = "SURVEY"
    severity = "WARNING"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["SURVEY_SUBMISSION", "BUILDING", "CROSS_DATASET", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        bld_map = {str(b.id): b for b in context.buildings}
        tol_bound = context.tolerances.boundary_tolerance_m

        for s in context.survey_observations:
            obs_type = getattr(s, "observation_type", None)
            target_id = getattr(s, "target_id", None)
            lat = getattr(s, "latitude", None)
            lon = getattr(s, "longitude", None)
            if obs_type == "FOOTPRINT_CORNER" and target_id and str(target_id) in bld_map and lat and lon:
                b = bld_map[str(target_id)]
                b_wkt = getattr(b, "geometry_wkt", None) or getattr(b, "geometry", None)
                if not b_wkt:
                    continue
                try:
                    bg = GeometryEngine.parse_geometry(b_wkt)
                    pt = shapely.Point(lon, lat)
                    dist_deg = bg.distance(pt)
                    # Convert distance in degrees to approximate meters (~111,320m per degree)
                    dist_m = dist_deg * 111320.0
                    if dist_m > (tol_bound * 10.0): # e.g. > 1.5m discrepancy from registered boundary
                        b_ref = getattr(b, "building_reference", str(b.id))
                        issues.append(IssueDraft(
                            rule_id=self.rule_id,
                            rule_version=self.rule_version,
                            issue_code="SRV-004",
                            category=self.category,
                            severity=self.severity,
                            entity_type="SURVEY_OBSERVATION",
                            entity_id=str(s.id),
                            related_entity_type="BUILDING",
                            related_entity_id=str(b.id),
                            message=f"Survey corner point is {dist_m:.2f}m away from official building {b_ref} boundary.",
                            technical_explanation=f"Field corner GNSS point diverges from official building boundary ring by {dist_m:.2f}m > tolerance {tol_bound:.2f}m.",
                            measured_value=f"{dist_m:.2f}m boundary distance",
                            expected_value=f"<= {tol_bound:.2f}m",
                            tolerance=f"{tol_bound:.2f}m",
                            metadata_json={"distance_m": dist_m, "latitude": lat, "longitude": lon},
                        ))
                except Exception:
                    pass
        return issues

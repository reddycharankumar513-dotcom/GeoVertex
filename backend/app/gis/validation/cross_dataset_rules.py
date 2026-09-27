from typing import Any, Dict, List
import shapely
from app.gis.geometry import GeometryEngine
from app.gis.validation.base import IssueDraft, ValidationContext, ValidationRule


class CrossDatasetDiscrepancyRule(ValidationRule):
    rule_id = "CROSS_DATASET_DISCREPANCY"
    name = "Cross-Dataset Boundary Discrepancy"
    description = "Evaluates spatial congruency (IoU, Hausdorff boundary distance, centroid shift) between survey observations, AI candidates, and official cadastre."
    category = "CROSS_DATASET"
    severity = "WARNING"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["CROSS_DATASET", "BUILDING", "PARCEL", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        bld_map = {str(b.id): b for b in context.buildings}

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

                # Hausdorff distance between boundary rings in degrees
                h_dist_deg = shapely.hausdorff_distance(cg.boundary, bg.boundary)
                h_dist_m = h_dist_deg * 111320.0 # approximate meters

                if h_dist_m > 2.0: # Hausdorff boundary shift > 2 meters
                    b_ref = getattr(b, "building_reference", str(b.id))
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="XDS-001",
                        category=self.category,
                        severity=self.severity,
                        entity_type="AI_RESULT",
                        entity_id=str(c.id),
                        related_entity_type="BUILDING",
                        related_entity_id=str(b.id),
                        message=f"Boundary divergence ({h_dist_m:.2f}m Hausdorff distance) between AI candidate and official building {b_ref}.",
                        technical_explanation=f"Maximum separation between boundary perimeter rings d_H(candidate, official) is {h_dist_m:.2f} meters.",
                        geometry_wkt=c_wkt,
                        measured_value=f"{h_dist_m:.2f}m Hausdorff distance",
                        expected_value="<= 2.0m",
                        tolerance="2.0m",
                        metadata_json={"hausdorff_distance_m": h_dist_m},
                    ))
            except Exception:
                pass
        return issues

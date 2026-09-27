import os
from typing import Any, Dict, List, Optional
from app.ai.change.base import BaseChangeDetector
from app.gis.temporal.geometry_diff import DeterministicGeometryComparator
from app.gis.temporal.attribute_diff import AttributeComparator
from app.gis.temporal.significance import SignificanceEvaluator
from app.models.temporal import ChangeType, ChangeSignificance


class DeterministicChangeDetector(BaseChangeDetector):
    """Performs deterministic vector geometry and structured attribute change detection."""

    def __init__(self):
        super().__init__(model_id="DETERMINISTIC_GEOM_DIFF", version="1.0.0")

    def is_configured(self) -> bool:
        return True

    def detect_changes(
        self,
        baseline_data: Dict[str, Any],
        comparison_data: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        entity_type = comparison_data.get("entity_type") or baseline_data.get("entity_type") or "BUILDING"
        entity_id = comparison_data.get("entity_id") or baseline_data.get("entity_id")

        base_wkt = baseline_data.get("geometry_wkt")
        curr_wkt = comparison_data.get("geometry_wkt")

        base_attrs = baseline_data.get("attributes", {}) or {}
        curr_attrs = comparison_data.get("attributes", {}) or {}

        # 1. Geometry Difference Analysis
        diff_res = DeterministicGeometryComparator.compare_geometries(base_wkt, curr_wkt)
        mag = diff_res.to_magnitude_dict()

        # Check for Building additions/removals/expansions/reductions
        if entity_type == "BUILDING":
            if not base_wkt and curr_wkt:
                # Newly added building
                sig = SignificanceEvaluator.evaluate(ChangeType.BUILDING_ADDED.value, mag)
                candidates.append({
                    "change_type": ChangeType.BUILDING_ADDED.value,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "geometry_wkt": diff_res.added_geometry_wkt or curr_wkt,
                    "baseline_geometry_wkt": None,
                    "comparison_geometry_wkt": curr_wkt,
                    "magnitude": mag,
                    "significance": sig.value,
                    "confidence": 1.0,
                    "evidence": [{
                        "source_type": "OFFICIAL_SNAPSHOT",
                        "description": "Building newly present in comparison dataset",
                        "area_sqm": diff_res.current_area,
                    }],
                })
            elif base_wkt and not curr_wkt:
                # Building removed
                sig = SignificanceEvaluator.evaluate(ChangeType.BUILDING_REMOVED.value, mag)
                candidates.append({
                    "change_type": ChangeType.BUILDING_REMOVED.value,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "geometry_wkt": diff_res.removed_geometry_wkt or base_wkt,
                    "baseline_geometry_wkt": base_wkt,
                    "comparison_geometry_wkt": None,
                    "magnitude": mag,
                    "significance": sig.value,
                    "confidence": 1.0,
                    "evidence": [{
                        "source_type": "OFFICIAL_SNAPSHOT",
                        "description": "Building no longer present in comparison dataset",
                        "area_sqm": diff_res.baseline_area,
                    }],
                })
            elif base_wkt and curr_wkt and abs(diff_res.area_difference) > 1.0:
                # Footprint expansion or reduction
                ch_type = (
                    ChangeType.BUILDING_EXPANDED.value
                    if diff_res.area_difference > 0
                    else ChangeType.BUILDING_REDUCED.value
                )
                sig = SignificanceEvaluator.evaluate(ch_type, mag)
                candidates.append({
                    "change_type": ch_type,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "geometry_wkt": (
                        diff_res.added_geometry_wkt
                        if diff_res.area_difference > 0
                        else diff_res.removed_geometry_wkt
                    ) or diff_res.symmetric_diff_wkt,
                    "baseline_geometry_wkt": base_wkt,
                    "comparison_geometry_wkt": curr_wkt,
                    "magnitude": mag,
                    "significance": sig.value,
                    "confidence": 1.0,
                    "evidence": [{
                        "source_type": "GEOMETRY_DIFF",
                        "description": f"Building footprint altered by {diff_res.area_difference:+.2f} m² ({diff_res.area_change_percentage:+.1f}%)",
                        "iou": diff_res.iou,
                    }],
                })
            elif base_wkt and curr_wkt and diff_res.iou < 0.95:
                # Boundary shifted without massive area change
                sig = SignificanceEvaluator.evaluate(ChangeType.BUILDING_GEOMETRY_CHANGED.value, mag)
                candidates.append({
                    "change_type": ChangeType.BUILDING_GEOMETRY_CHANGED.value,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "geometry_wkt": diff_res.symmetric_diff_wkt,
                    "baseline_geometry_wkt": base_wkt,
                    "comparison_geometry_wkt": curr_wkt,
                    "magnitude": mag,
                    "significance": sig.value,
                    "confidence": 1.0,
                    "evidence": [{
                        "source_type": "GEOMETRY_DIFF",
                        "description": f"Boundary displacement of {diff_res.boundary_displacement_m:.2f}m detected (IoU: {diff_res.iou:.3f})",
                    }],
                })

        # Parcel geometry changes
        elif entity_type == "PARCEL":
            if base_wkt and curr_wkt and (abs(diff_res.area_difference) > 1.0 or diff_res.iou < 0.98):
                sig = SignificanceEvaluator.evaluate(ChangeType.PARCEL_GEOMETRY_CHANGED.value, mag)
                candidates.append({
                    "change_type": ChangeType.PARCEL_GEOMETRY_CHANGED.value,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "geometry_wkt": diff_res.symmetric_diff_wkt,
                    "baseline_geometry_wkt": base_wkt,
                    "comparison_geometry_wkt": curr_wkt,
                    "magnitude": mag,
                    "significance": sig.value,
                    "confidence": 1.0,
                    "evidence": [{
                        "source_type": "GEOMETRY_DIFF",
                        "description": f"Parcel boundary adjusted between comparative records. Area delta: {diff_res.area_difference:+.2f} m²",
                    }],
                })

        # 2. Attribute Differences (Height, Floor Count, Land Use)
        attr_diffs = AttributeComparator.compare_attributes(base_attrs, curr_attrs)
        for ad in attr_diffs:
            if ad.attribute_name in ["height", "height_estimate"]:
                try:
                    h_old = float(ad.old_value or 0)
                    h_new = float(ad.new_value or 0)
                    h_diff = h_new - h_old
                    h_mag = {
                        "old_value": h_old,
                        "new_value": h_new,
                        "height_difference_m": round(h_diff, 2),
                    }
                    sig = SignificanceEvaluator.evaluate(ChangeType.BUILDING_HEIGHT_CHANGED.value, h_mag)
                    candidates.append({
                        "change_type": ChangeType.BUILDING_HEIGHT_CHANGED.value,
                        "entity_type": entity_type,
                        "entity_id": entity_id,
                        "geometry_wkt": curr_wkt or base_wkt,
                        "baseline_geometry_wkt": base_wkt,
                        "comparison_geometry_wkt": curr_wkt,
                        "magnitude": h_mag,
                        "significance": sig.value,
                        "confidence": 0.95,
                        "evidence": [{
                            "source_type": "ATTRIBUTE_DIFF",
                            "attribute": ad.attribute_name,
                            "description": f"Building height changed from {h_old:.1f}m to {h_new:.1f}m (delta: {h_diff:+.1f}m)",
                        }],
                    })
                except Exception:
                    pass

            elif ad.attribute_name in ["floor_count"]:
                try:
                    fc_old = int(ad.old_value or 0)
                    fc_new = int(ad.new_value or 0)
                    fc_diff = fc_new - fc_old
                    fc_mag = {
                        "baseline_floor_count": fc_old,
                        "comparison_floor_count": fc_new,
                        "floor_count_difference": fc_diff,
                    }
                    sig = SignificanceEvaluator.evaluate(ChangeType.FLOOR_COUNT_CHANGED.value, fc_mag)
                    candidates.append({
                        "change_type": ChangeType.FLOOR_COUNT_CHANGED.value,
                        "entity_type": entity_type,
                        "entity_id": entity_id,
                        "geometry_wkt": curr_wkt or base_wkt,
                        "baseline_geometry_wkt": base_wkt,
                        "comparison_geometry_wkt": curr_wkt,
                        "magnitude": fc_mag,
                        "significance": sig.value,
                        "confidence": 0.95,
                        "evidence": [{
                            "source_type": "ATTRIBUTE_DIFF",
                            "attribute": ad.attribute_name,
                            "description": f"Floor count changed from {fc_old} to {fc_new} floors (delta: {fc_diff:+d})",
                        }],
                    })
                except Exception:
                    pass
            else:
                # General attribute change
                ch_type = (
                    ChangeType.PARCEL_ATTRIBUTE_CHANGED.value
                    if entity_type == "PARCEL"
                    else ChangeType.PROPERTY_ATTRIBUTE_CHANGED.value
                )
                candidates.append({
                    "change_type": ch_type,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "geometry_wkt": curr_wkt or base_wkt,
                    "baseline_geometry_wkt": base_wkt,
                    "comparison_geometry_wkt": curr_wkt,
                    "magnitude": {
                        "attribute_name": ad.attribute_name,
                        "old_value": ad.old_value,
                        "new_value": ad.new_value,
                    },
                    "significance": ChangeSignificance.MINOR.value,
                    "confidence": 1.0,
                    "evidence": [{
                        "source_type": "ATTRIBUTE_DIFF",
                        "description": f"Attribute '{ad.attribute_name}' modified from '{ad.old_value}' to '{ad.new_value}'",
                    }],
                })

        return candidates


class AIChangeDetector(BaseChangeDetector):
    """AI Siamese / U-Net remote sensing change detector enforcing strict No Fake AI."""

    def __init__(self, model_id: str = "SIAMESE_UNET_CHANGE_V1", weights_path: Optional[str] = None):
        super().__init__(model_id=model_id, version="1.0.0")
        self.weights_path = weights_path or os.environ.get("GEOVERTEX_CHANGE_MODEL_PATH")

    def is_configured(self) -> bool:
        return bool(self.weights_path and os.path.exists(self.weights_path))

    def detect_changes(
        self,
        baseline_data: Dict[str, Any],
        comparison_data: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if not self.is_configured():
            # Mandatory No Fake AI: return explicit unconfigured state
            return [{
                "change_type": ChangeType.UNKNOWN_CHANGE.value,
                "status": "MODEL_NOT_CONFIGURED",
                "message": f"MODEL_NOT_CONFIGURED: AI Change Detection model '{self.model_id}' weights not configured at '{self.weights_path}'. Set GEOVERTEX_CHANGE_MODEL_PATH to activate deep learning inference.",
                "significance": ChangeSignificance.UNKNOWN.value,
                "confidence": 0.0,
                "magnitude": {},
                "evidence": [],
            }]

        # Real ML inference would load weights and execute forward pass here
        return []

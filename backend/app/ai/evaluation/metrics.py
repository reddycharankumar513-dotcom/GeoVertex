from typing import Any, Dict, List
import numpy as np
from shapely.geometry import Polygon
from app.ai.preprocessing.geo_processor import GEOD, geo_preprocessor


def compute_iou(poly1: Any, poly2: Any) -> float:
    """Computes Intersection over Union between two geometries."""
    p1 = geo_preprocessor.parse_geometry(poly1)
    p2 = geo_preprocessor.parse_geometry(poly2)

    inter = p1.intersection(p2)
    union = p1.union(p2)

    if union.is_empty or union.area == 0:
        return 0.0
    return float(inter.area / union.area)


def compute_evaluation_metrics(
    predictions: List[Any],
    ground_truths: List[Any],
    iou_threshold: float = 0.5,
) -> Dict[str, Any]:
    """Computes standard spatial evaluation metrics: IoU, Precision, Recall, F1, Area Error, Boundary Error.
    
    predictions: List of candidate geometry objects (WKT / GeoJSON / Polygon)
    ground_truths: List of ground-truth geometry objects
    """
    n = len(predictions)
    if n == 0 or len(ground_truths) != n:
        return {
            "sample_count": 0,
            "mean_iou": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0,
            "mean_area_error_sqm": 0.0,
            "mean_boundary_error_m": 0.0,
        }

    ious: List[float] = []
    area_errors: List[float] = []
    boundary_errors: List[float] = []
    true_positives = 0
    false_positives = 0
    false_negatives = 0

    for pred_geom, gt_geom in zip(predictions, ground_truths):
        try:
            p_poly = geo_preprocessor.parse_geometry(pred_geom)
            g_poly = geo_preprocessor.parse_geometry(gt_geom)

            # IoU
            iou = compute_iou(p_poly, g_poly)
            ious.append(iou)

            if iou >= iou_threshold:
                true_positives += 1
            else:
                false_positives += 1
                false_negatives += 1

            # Geodesic area error
            p_area, _ = GEOD.geometry_area_perimeter(p_poly)
            g_area, _ = GEOD.geometry_area_perimeter(g_poly)
            area_errors.append(abs(abs(p_area) - abs(g_area)))

            # Hausdorff distance
            h_deg = p_poly.hausdorff_distance(g_poly)
            boundary_errors.append(h_deg * 111320.0)
        except Exception:
            ious.append(0.0)
            false_positives += 1

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "sample_count": n,
        "mean_iou": round(float(np.mean(ious)), 4),
        "median_iou": round(float(np.median(ious)), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1_score": round(float(f1), 4),
        "mean_area_error_sqm": round(float(np.mean(area_errors)), 2) if area_errors else 0.0,
        "mean_boundary_error_m": round(float(np.mean(boundary_errors)), 2) if boundary_errors else 0.0,
        "iou_threshold": iou_threshold,
    }

from typing import Any, Dict, Optional
from shapely.geometry import Polygon
from app.ai.preprocessing.geo_processor import GEOD, geo_preprocessor


class CadastralComparator:
    """Computes rigorous deterministic comparison metrics between AI candidate and official cadastre."""

    def compare_geometries(
        self,
        candidate_geom: Any,
        official_geom: Any,
    ) -> Dict[str, Any]:
        """Calculates IoU, intersection area, union area, area discrepancy, and boundary difference.
        
        Note: These are deterministic spatial metrics, NOT claims of ground truth accuracy.
        """
        cand_poly = geo_preprocessor.parse_geometry(candidate_geom)
        off_poly = geo_preprocessor.parse_geometry(official_geom)

        cand_area_sqm, _ = GEOD.geometry_area_perimeter(cand_poly)
        off_area_sqm, _ = GEOD.geometry_area_perimeter(off_poly)
        cand_area_sqm = abs(cand_area_sqm)
        off_area_sqm = abs(off_area_sqm)

        # Intersection & Union
        intersection = cand_poly.intersection(off_poly)
        union = cand_poly.union(off_poly)

        inter_area_sqm = 0.0
        if not intersection.is_empty:
            raw_inter, _ = GEOD.geometry_area_perimeter(intersection)
            inter_area_sqm = abs(raw_inter)

        union_area_sqm = 0.0
        if not union.is_empty:
            raw_union, _ = GEOD.geometry_area_perimeter(union)
            union_area_sqm = abs(raw_union)

        iou = (inter_area_sqm / union_area_sqm) if union_area_sqm > 0 else 0.0

        # Hausdorff boundary difference in degrees, converted to approx meters
        boundary_diff_deg = cand_poly.hausdorff_distance(off_poly)
        boundary_diff_m = boundary_diff_deg * 111320.0  # approximate meters at equator/mid-latitude

        area_diff_sqm = abs(cand_area_sqm - off_area_sqm)
        area_diff_ratio = (area_diff_sqm / off_area_sqm) if off_area_sqm > 0 else 0.0

        return {
            "iou": round(float(iou), 4),
            "intersection_area_sqm": round(float(inter_area_sqm), 2),
            "union_area_sqm": round(float(union_area_sqm), 2),
            "area_diff_sqm": round(float(area_diff_sqm), 2),
            "area_diff_ratio": round(float(area_diff_ratio), 4),
            "boundary_diff_m": round(float(boundary_diff_m), 2),
            "official_area_sqm": round(float(off_area_sqm), 2),
            "candidate_area_sqm": round(float(cand_area_sqm), 2),
        }

    def compute_composite_confidence(
        self,
        model_confidence: float,
        geometry_quality: float,
        source_quality: float,
    ) -> Dict[str, Any]:
        """Calculates transparent weighted composite confidence without hiding components.
        
        Formula:
            Composite = 0.50 * model_confidence + 0.30 * geometry_quality + 0.20 * source_quality
        """
        m_conf = max(0.0, min(1.0, float(model_confidence)))
        g_qual = max(0.0, min(1.0, float(geometry_quality)))
        s_qual = max(0.0, min(1.0, float(source_quality)))

        composite = (0.50 * m_conf) + (0.30 * g_qual) + (0.20 * s_qual)
        composite = round(max(0.0, min(1.0, composite)), 3)

        return {
            "composite_confidence": composite,
            "components": {
                "model_confidence": round(m_conf, 3),
                "geometry_quality": round(g_qual, 3),
                "source_quality": round(s_qual, 3),
            },
        }


cadastral_comparator = CadastralComparator()

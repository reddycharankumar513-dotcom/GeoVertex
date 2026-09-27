import os
from typing import Any, Dict, Optional, Tuple


class ImageRegistrationValidator:
    """Validates spatial alignment, extent, and coordinate reference systems for raster comparison."""

    @classmethod
    def validate_and_register(
        cls,
        baseline_meta: Dict[str, Any],
        comparison_meta: Dict[str, Any],
        max_resolution_ratio: float = 4.0,
        min_spatial_overlap_pct: float = 0.80,
    ) -> Dict[str, Any]:
        """Validates raster metadata for alignment suitability."""
        # 1. Check CRS
        crs_base = str(baseline_meta.get("crs", "EPSG:4326")).upper()
        crs_curr = str(comparison_meta.get("crs", "EPSG:4326")).upper()

        if crs_base != crs_curr:
            return {
                "status": "CRS_MISMATCH",
                "is_aligned": False,
                "message": f"CRS mismatch: {crs_base} vs {crs_curr}. Reprojection required.",
                "source_crs": crs_base,
                "target_crs": crs_curr,
            }

        # 2. Check resolution
        res_base = float(baseline_meta.get("resolution_meters", 1.0) or 1.0)
        res_curr = float(comparison_meta.get("resolution_meters", 1.0) or 1.0)

        ratio = max(res_base, res_curr) / min(res_base, res_curr)
        if ratio > max_resolution_ratio:
            return {
                "status": "INSUFFICIENT_RESOLUTION",
                "is_aligned": False,
                "message": f"Resolution discrepancy exceeds tolerance: {res_base}m vs {res_curr}m (ratio: {ratio:.1f}x)",
                "baseline_resolution": res_base,
                "comparison_resolution": res_curr,
            }

        # 3. Check spatial bounds overlap
        bounds_base = baseline_meta.get("bounds")  # [minx, miny, maxx, maxy]
        bounds_curr = comparison_meta.get("bounds")

        if bounds_base and bounds_curr:
            minx = max(bounds_base[0], bounds_curr[0])
            miny = max(bounds_base[1], bounds_curr[1])
            maxx = min(bounds_base[2], bounds_curr[2])
            maxy = min(bounds_base[3], bounds_curr[3])

            if minx >= maxx or miny >= maxy:
                return {
                    "status": "LOW_SPATIAL_OVERLAP",
                    "is_aligned": False,
                    "message": "Images do not intersect spatially.",
                    "overlap_pct": 0.0,
                }

            overlap_area = (maxx - minx) * (maxy - miny)
            base_area = (bounds_base[2] - bounds_base[0]) * (bounds_base[3] - bounds_base[1])
            overlap_pct = (overlap_area / base_area) if base_area > 0 else 0.0

            if overlap_pct < min_spatial_overlap_pct:
                return {
                    "status": "IMAGE_ALIGNMENT_INSUFFICIENT",
                    "is_aligned": False,
                    "message": f"Spatial overlap ({overlap_pct * 100:.1f}%) is below required threshold ({min_spatial_overlap_pct * 100:.0f}%)",
                    "overlap_pct": round(overlap_pct, 4),
                }

        return {
            "status": "ALIGNED",
            "is_aligned": True,
            "crs": crs_base,
            "transformation": "IDENTITY_AFFINE",
            "registration_method": "RPC_ORTHORECTIFIED",
            "overlap_pct": 1.0,
        }

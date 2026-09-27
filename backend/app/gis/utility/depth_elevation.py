"""Depth and elevation calculator and vertical validator for underground utility assets."""

from typing import Dict, List, Optional, Tuple


class DepthElevationCalculator:
    """Deterministic vertical reference, depth, elevation, and slope engine."""

    @staticmethod
    def compute_depth(
        ground_elevation: Optional[float],
        centerline_elevation: Optional[float],
    ) -> Optional[float]:
        """Compute depth below ground in meters: Depth = Ground Elevation - Centerline Elevation.
        
        Returns None (UNKNOWN) if either value is missing. Never fabricates depth.
        """
        if ground_elevation is None or centerline_elevation is None:
            return None
        return round(float(ground_elevation) - float(centerline_elevation), 3)

    @staticmethod
    def compute_centerline_elevation(
        ground_elevation: Optional[float],
        depth: Optional[float],
    ) -> Optional[float]:
        """Compute centerline elevation in meters: Centerline = Ground Elevation - Depth.
        
        Returns None (UNKNOWN) if either value is missing.
        """
        if ground_elevation is None or depth is None:
            return None
        return round(float(ground_elevation) - float(depth), 3)

    @staticmethod
    def compute_slope(
        elevation_start: Optional[float],
        elevation_end: Optional[float],
        length_meters: float,
    ) -> Optional[float]:
        """Compute grade slope percentage: Slope (%) = ((Elev_start - Elev_end) / Length) * 100.
        
        Positive slope indicates downward flow from start to end.
        """
        if elevation_start is None or elevation_end is None or length_meters <= 0.001:
            return None
        delta = float(elevation_start) - float(elevation_end)
        return round((delta / float(length_meters)) * 100.0, 3)

    @staticmethod
    def validate_vertical_bounds(
        depth: Optional[float],
        ground_elevation: Optional[float] = None,
        centerline_elevation: Optional[float] = None,
        min_expected_depth_m: float = 0.2,
        max_expected_depth_m: float = 30.0,
    ) -> List[Dict[str, str]]:
        """Validate vertical consistency against physical feasibility rules."""
        issues: List[Dict[str, str]] = []

        if depth is not None:
            if depth < 0.0:
                issues.append({
                    "code": "UTILITY_INVALID_DEPTH",
                    "severity": "ERROR",
                    "message": f"Negative depth ({depth}m) reported for subsurface asset.",
                })
            elif depth < min_expected_depth_m:
                issues.append({
                    "code": "UTILITY_INSUFFICIENT_COVER",
                    "severity": "WARNING",
                    "message": f"Depth of cover ({depth}m) is below standard minimum threshold ({min_expected_depth_m}m).",
                })
            elif depth > max_expected_depth_m:
                issues.append({
                    "code": "UTILITY_DEPTH_OUTSIDE_EXPECTED_RANGE",
                    "severity": "WARNING",
                    "message": f"Depth ({depth}m) exceeds typical municipal trench limit ({max_expected_depth_m}m).",
                })

        if ground_elevation is not None and centerline_elevation is not None:
            derived_depth = ground_elevation - centerline_elevation
            if derived_depth < -0.01:
                issues.append({
                    "code": "UTILITY_ELEVATION_INVERSION",
                    "severity": "ERROR",
                    "message": f"Centerline elevation ({centerline_elevation}m) is higher than ground elevation ({ground_elevation}m).",
                })
            if depth is not None and abs(derived_depth - depth) > 0.05:
                issues.append({
                    "code": "UTILITY_DEPTH_ELEVATION_DISCREPANCY",
                    "severity": "WARNING",
                    "message": f"Explicit depth ({depth}m) differs from ground-centerline difference ({derived_depth:.3f}m) by > 5cm.",
                })

        return issues

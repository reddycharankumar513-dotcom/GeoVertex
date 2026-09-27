from typing import Any, Dict, List, Optional, Tuple
from shapely import wkt
from shapely.geometry import Polygon
from app.ai.preprocessing.geo_processor import GEOD, geo_preprocessor


class DeterministicGeometryValidator:
    """Performs rigorous deterministic PostGIS/Shapely spatial checks on candidate geometries."""

    def __init__(
        self,
        min_area_sqm: float = 5.0,
        max_area_sqm: float = 100000.0,
        expected_srid: int = 4326,
    ):
        self.min_area_sqm = min_area_sqm
        self.max_area_sqm = max_area_sqm
        self.expected_srid = expected_srid

    def validate_candidate_polygon(
        self,
        polygon_input: Any,
        parent_parcel_geom: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Validates topological integrity, area boundaries, and spatial containment.
        
        Returns validation report with status (VALID, INVALID, WARNING) and issues list.
        """
        issues: List[Dict[str, str]] = []
        status = "VALID"

        try:
            poly = geo_preprocessor.parse_geometry(polygon_input)
        except Exception as e:
            return {
                "status": "INVALID",
                "is_valid": False,
                "is_empty": True,
                "issues": [{"code": "GEOMETRY_PARSE_ERROR", "message": str(e), "severity": "ERROR"}],
            }

        # Check 1: Empty geometry
        if poly.is_empty:
            issues.append({"code": "GEOMETRY_EMPTY", "message": "Geometry is empty", "severity": "ERROR"})
            status = "INVALID"

        # Check 2: OGC Validity (self-intersections, bowties)
        if not poly.is_valid:
            issues.append({
                "code": "TOPOLOGY_SELF_INTERSECTION",
                "message": "Geometry is topologically invalid according to OGC standards",
                "severity": "ERROR",
            })
            status = "INVALID"

        # Check 3: Area boundaries
        area_sqm, perimeter_m = GEOD.geometry_area_perimeter(poly)
        abs_area = abs(area_sqm)

        if abs_area < self.min_area_sqm:
            issues.append({
                "code": "AREA_BELOW_MINIMUM",
                "message": f"Calculated area ({abs_area:.2f} m²) is below minimum threshold ({self.min_area_sqm} m²)",
                "severity": "ERROR",
            })
            status = "INVALID"
        elif abs_area > self.max_area_sqm:
            issues.append({
                "code": "AREA_EXCEEDS_MAXIMUM",
                "message": f"Calculated area ({abs_area:.2f} m²) exceeds maximum threshold ({self.max_area_sqm} m²)",
                "severity": "WARNING",
            })
            if status != "INVALID":
                status = "WARNING"

        # Check 4: Coordinate bounds (WGS 84 lon/lat ranges)
        minx, miny, maxx, maxy = poly.bounds
        if not (-180.0 <= minx <= 180.0 and -180.0 <= maxx <= 180.0 and -90.0 <= miny <= 90.0 and -90.0 <= maxy <= 90.0):
            issues.append({
                "code": "COORDINATES_OUT_OF_BOUNDS",
                "message": f"Coordinates exceed EPSG:4326 WGS84 range: [{minx}, {miny}, {maxx}, {maxy}]",
                "severity": "ERROR",
            })
            status = "INVALID"

        # Check 5: Optional parent parcel containment check
        is_contained_in_parcel = None
        if parent_parcel_geom is not None:
            try:
                parcel_poly = geo_preprocessor.parse_geometry(parent_parcel_geom)
                if not poly.within(parcel_poly):
                    # Check overlap percentage
                    intersection = poly.intersection(parcel_poly)
                    overlap_ratio = intersection.area / poly.area if poly.area > 0 else 0
                    if overlap_ratio < 0.95:
                        issues.append({
                            "code": "ENCROACHMENT_PARCEL_BOUNDARY",
                            "message": f"Candidate building extends beyond parcel boundary ({overlap_ratio * 100:.1f}% inside)",
                            "severity": "WARNING",
                        })
                        if status != "INVALID":
                            status = "WARNING"
                is_contained_in_parcel = poly.within(parcel_poly)
            except Exception:
                pass

        # Calculate geometric quality rating (0.0 to 1.0)
        # Isoperimetric quotient: 4 * pi * area / (perimeter^2) for compactness
        compactness = 0.0
        if perimeter_m > 0:
            compactness = min(1.0, max(0.0, (4.0 * 3.14159 * abs_area) / (abs(perimeter_m) ** 2)))
        geometry_quality = round(0.5 + (0.5 * compactness) if status == "VALID" else (0.3 if status == "WARNING" else 0.0), 3)

        return {
            "status": status,
            "is_valid": poly.is_valid,
            "is_empty": poly.is_empty,
            "srid": self.expected_srid,
            "area_sqm": round(abs_area, 2),
            "perimeter_m": round(abs(perimeter_m), 2),
            "vertex_count": len(poly.exterior.coords),
            "geometry_quality_score": geometry_quality,
            "is_contained_in_parcel": is_contained_in_parcel,
            "issues": issues,
        }


deterministic_validator = DeterministicGeometryValidator()

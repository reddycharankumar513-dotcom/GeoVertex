from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from shapely import wkt
from shapely.geometry import Polygon, MultiPolygon, mapping
from shapely.validation import make_valid
from app.ai.base import OutputGeometryInvalidError
from app.ai.preprocessing.geo_processor import GEOD


class BuildingPolygonizer:
    """Converts prediction arrays or raw candidate geometries into clean cadastral polygons."""

    def __init__(
        self,
        min_area_sqm: float = 10.0,
        simplification_tolerance_deg: float = 0.00002,  # approx ~2 meters at mid-latitudes
    ):
        self.min_area_sqm = min_area_sqm
        self.simplification_tolerance = simplification_tolerance_deg

    def postprocess_polygon(
        self,
        raw_polygon: Polygon,
        simplification_tolerance: Optional[float] = None,
        min_area: Optional[float] = None,
    ) -> Tuple[Polygon, Dict[str, Any]]:
        """Cleans, repairs, filters small artifacts, and simplifies candidate geometry.
        
        Returns:
            (processed_polygon, transformation_metadata)
        """
        tolerance = simplification_tolerance if simplification_tolerance is not None else self.simplification_tolerance
        min_sqm = min_area if min_area is not None else self.min_area_sqm

        if raw_polygon is None or raw_polygon.is_empty:
            raise OutputGeometryInvalidError("Candidate polygon is empty or null")

        # Step 1: Repair self-intersections or bowtie rings if invalid
        repaired = raw_polygon
        was_repaired = False
        if not raw_polygon.is_valid:
            repaired = make_valid(raw_polygon)
            was_repaired = True

        if repaired.is_empty:
            raise OutputGeometryInvalidError("Candidate polygon could not be made valid")

        # Extract largest polygon if geometry became MultiPolygon
        if repaired.geom_type == "MultiPolygon":
            repaired = max(repaired.geoms, key=lambda p: p.area)
        elif repaired.geom_type == "GeometryCollection":
            polys = [g for g in repaired.geoms if g.geom_type == "Polygon"]
            if not polys:
                raise OutputGeometryInvalidError("Postprocessed geometry contains no polygons")
            repaired = max(polys, key=lambda p: p.area)
        elif repaired.geom_type != "Polygon":
            raise OutputGeometryInvalidError(f"Postprocessed geometry is not a Polygon: {repaired.geom_type}")

        # Step 2: Douglas-Peucker simplification preserving topology
        simplified = repaired.simplify(tolerance, preserve_topology=True)
        if simplified.geom_type != "Polygon":
            simplified = repaired

        # Step 3: Check minimum area
        area_sqm, perimeter_m = GEOD.geometry_area_perimeter(simplified)
        abs_area = abs(area_sqm)
        if abs_area < min_sqm:
            raise OutputGeometryInvalidError(
                f"Candidate polygon area ({abs_area:.2f} m²) is below minimum threshold ({min_sqm} m²)"
            )

        metadata = {
            "was_repaired": was_repaired,
            "simplification_tolerance_deg": tolerance,
            "min_area_threshold_sqm": min_sqm,
            "raw_vertex_count": len(raw_polygon.exterior.coords),
            "processed_vertex_count": len(simplified.exterior.coords),
            "area_sqm": round(abs_area, 2),
            "perimeter_m": round(abs(perimeter_m), 2),
        }

        return simplified, metadata


polygonizer = BuildingPolygonizer()

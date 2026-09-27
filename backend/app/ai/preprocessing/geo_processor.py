from typing import Any, Dict, List, Optional, Tuple
import pyproj
from shapely import wkt
from shapely.geometry import Polygon, MultiPolygon, box, mapping, shape
from shapely.ops import transform
from app.ai.base import InputInvalidError

# Geodesic Calculator for accurate EPSG:4326 metric area & perimeter
GEOD = pyproj.Geod(ellps="WGS84")


class GeospatialPreprocessor:
    """Preprocesses cadastral geometries, AOI buffers, and spatial reference systems."""

    def __init__(self, target_srid: int = 4326):
        self.target_srid = target_srid

    def parse_geometry(self, geom_input: Any) -> Polygon:
        """Parses GeoJSON dict, WKT string, or Shapely Polygon into a valid Shapely Polygon."""
        if geom_input is None:
            raise InputInvalidError("Geometry input cannot be None")

        try:
            if isinstance(geom_input, str):
                geom = wkt.loads(geom_input)
            elif isinstance(geom_input, dict):
                geom = shape(geom_input)
            elif hasattr(geom_input, "geom_type"):
                geom = geom_input
            else:
                raise ValueError("Unsupported geometry format")

            if geom.is_empty:
                raise InputInvalidError("Input geometry is empty")

            if geom.geom_type == "MultiPolygon":
                # Extract largest polygon in multipolygon
                geom = max(geom.geoms, key=lambda p: p.area)

            if geom.geom_type != "Polygon":
                raise InputInvalidError(f"Expected Polygon geometry, got {geom.geom_type}")

            return geom
        except Exception as e:
            if isinstance(e, InputInvalidError):
                raise
            raise InputInvalidError(f"Failed to parse geometry: {str(e)}")

    def compute_aoi(
        self,
        target_geometry: Any,
        buffer_meters: float = 15.0,
    ) -> Dict[str, Any]:
        """Calculates Area of Interest (AOI) bounding box and buffered envelope in EPSG:4326."""
        polygon = self.parse_geometry(target_geometry)

        # Approximate degree offset for buffer_meters at equator/mid-latitudes: 1 deg ~ 111,320m
        deg_buffer = buffer_meters / 111320.0
        buffered = polygon.buffer(deg_buffer)
        minx, miny, maxx, maxy = buffered.bounds
        bbox_geom = box(minx, miny, maxx, maxy)

        # Geodesic metric area of target
        area_sqm, perimeter_m = GEOD.geometry_area_perimeter(polygon)

        return {
            "source_srid": self.target_srid,
            "target_srid": self.target_srid,
            "bounds": [minx, miny, maxx, maxy],
            "bbox_geojson": mapping(bbox_geom),
            "buffered_wkt": buffered.wkt,
            "target_wkt": polygon.wkt,
            "target_area_sqm": abs(area_sqm),
            "target_perimeter_m": abs(perimeter_m),
            "buffer_meters": buffer_meters,
        }

    def clip_to_aoi(self, candidate_geom: Any, aoi_bounds: List[float]) -> Optional[Polygon]:
        """Clips candidate geometry to the bounding box of the Area of Interest."""
        cand_poly = self.parse_geometry(candidate_geom)
        aoi_box = box(*aoi_bounds)

        intersection = cand_poly.intersection(aoi_box)
        if intersection.is_empty:
            return None

        if intersection.geom_type == "Polygon":
            return intersection
        elif intersection.geom_type == "MultiPolygon":
            return max(intersection.geoms, key=lambda p: p.area)
        return None


geo_preprocessor = GeospatialPreprocessor()

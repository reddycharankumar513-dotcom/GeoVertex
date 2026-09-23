import json
import math
from typing import Any, Dict, List, Optional, Tuple, Union
import pyproj
from pydantic import BaseModel
import shapely
from shapely.geometry import shape, mapping, Point, Polygon, MultiPolygon, box
from shapely import wkt
from shapely.validation import explain_validity


class ValidationErrorItem(BaseModel):
    code: str
    message: str


class ValidationWarningItem(BaseModel):
    code: str
    message: str


class ValidationResult(BaseModel):
    valid: bool
    errors: List[ValidationErrorItem] = []
    warnings: List[ValidationWarningItem] = []


class GeometryEngine:
    """Authoritative 2D GIS geometry engine for GeoVertex.
    Provides CRS normalization, PostGIS compatibility, geodesic area/centroid computation,
    and topology verification using Shapely and PyProj.
    """

    # WGS84 Geodetic reference ellipsoid for authoritative metric calculations
    GEOD = pyproj.Geod(ellps="WGS84")

    @classmethod
    def parse_geometry(
        cls,
        geom_input: Union[Dict[str, Any], str, shapely.Geometry],
        source_srid: int = 4326,
    ) -> shapely.Geometry:
        """Parses a geometry from GeoJSON dict, WKT string, or Shapely object,
        normalizing to EPSG:4326.
        """
        if isinstance(geom_input, shapely.Geometry):
            geom = geom_input
        elif isinstance(geom_input, dict):
            if "type" in geom_input and "coordinates" in geom_input:
                geom = shape(geom_input)
            elif "geometry" in geom_input:
                geom = shape(geom_input["geometry"])
            else:
                raise ValueError("Invalid GeoJSON geometry structure")
        elif isinstance(geom_input, str):
            clean_str = geom_input.strip()
            if clean_str.startswith("{"):
                geojson_dict = json.loads(clean_str)
                if "type" in geojson_dict and "coordinates" in geojson_dict:
                    geom = shape(geojson_dict)
                elif "geometry" in geojson_dict:
                    geom = shape(geojson_dict["geometry"])
                else:
                    raise ValueError("Invalid GeoJSON geometry string")
            else:
                geom = wkt.loads(clean_str)
        else:
            raise ValueError(f"Unsupported geometry format: {type(geom_input)}")

        if source_srid != 4326:
            geom = cls.transform_crs(geom, from_srid=source_srid, to_srid=4326)

        return geom

    @classmethod
    def transform_crs(
        cls,
        geom: shapely.Geometry,
        from_srid: int,
        to_srid: int = 4326,
    ) -> shapely.Geometry:
        """Reprojects a Shapely geometry between coordinate reference systems."""
        if from_srid == to_srid:
            return geom
        transformer = pyproj.Transformer.from_crs(
            f"EPSG:{from_srid}",
            f"EPSG:{to_srid}",
            always_xy=True,
        )
        return shapely.ops.transform(transformer.transform, geom)

    @classmethod
    def calculate_geodesic_area(cls, geom: shapely.Geometry) -> float:
        """Calculates authoritative ground area in square meters using WGS84 geodesic math."""
        if geom.is_empty:
            return 0.0
        try:
            area, _ = cls.GEOD.geometry_area_perimeter(geom)
            return round(abs(area), 2)
        except Exception:
            # Fallback for complex multi-polygons if needed
            return 0.0

    @classmethod
    def calculate_centroid(cls, geom: shapely.Geometry) -> Tuple[float, float]:
        """Calculates authoritative longitude and latitude centroid."""
        if geom.is_empty:
            return (0.0, 0.0)
        c = geom.centroid
        return (round(c.x, 7), round(c.y, 7))

    @classmethod
    def get_bbox(cls, geom: shapely.Geometry) -> Tuple[float, float, float, float]:
        """Returns bounding box coordinates (min_lon, min_lat, max_lon, max_lat)."""
        minx, miny, maxx, maxy = geom.bounds
        return (round(minx, 7), round(miny, 7), round(maxx, 7), round(maxy, 7))

    @classmethod
    def to_wkt(cls, geom: shapely.Geometry) -> str:
        """Converts Shapely geometry to WKT string."""
        return wkt.dumps(geom)

    @classmethod
    def to_geojson(cls, geom: shapely.Geometry) -> Dict[str, Any]:
        """Converts Shapely geometry to GeoJSON dict."""
        return mapping(geom)

    @classmethod
    def validate_geometry(
        cls,
        geom_input: Union[Dict[str, Any], str, shapely.Geometry],
        expected_type: Optional[str] = None,
        source_srid: int = 4326,
    ) -> ValidationResult:
        """Strict cadastral validation for geometry validity, self-intersections,
        coordinate validity, and geometry type.
        """
        errors: List[ValidationErrorItem] = []
        warnings: List[ValidationWarningItem] = []

        if geom_input is None:
            return ValidationResult(
                valid=False,
                errors=[ValidationErrorItem(code="MISSING_GEOMETRY", message="Geometry cannot be empty or null")],
            )

        try:
            geom = cls.parse_geometry(geom_input, source_srid=source_srid)
        except Exception as e:
            return ValidationResult(
                valid=False,
                errors=[ValidationErrorItem(code="PARSE_ERROR", message=f"Failed to parse geometry: {str(e)}")],
            )

        if geom.is_empty:
            errors.append(ValidationErrorItem(code="EMPTY_GEOMETRY", message="Geometry contains no coordinates"))
            return ValidationResult(valid=False, errors=errors, warnings=warnings)

        # Coordinate bounds check for EPSG:4326
        minx, miny, maxx, maxy = geom.bounds
        if minx < -180.0 or maxx > 180.0 or miny < -90.0 or maxy > 90.0:
            errors.append(
                ValidationErrorItem(
                    code="OUT_OF_BOUNDS_COORDINATES",
                    message=f"Coordinates out of bounds for WGS84: lon [{minx}, {maxx}], lat [{miny}, {maxy}]",
                )
            )

        # Shapely validity & self-intersection check
        if not geom.is_valid:
            reason = explain_validity(geom)
            code = "INVALID_GEOMETRY"
            if "Self-intersection" in reason or "Self-intersection" in reason:
                code = "SELF_INTERSECTION"
            elif "Ring Self-intersection" in reason:
                code = "RING_SELF_INTERSECTION"
            elif "Too few points" in reason:
                code = "DEGENERATE_RING"
            errors.append(ValidationErrorItem(code=code, message=f"Geometry topological error: {reason}"))

        # Expected geometry type check
        if expected_type:
            geom_type = geom.geom_type.upper()
            expected = expected_type.upper()
            if expected in ["POLYGON", "MULTIPOLYGON"]:
                if geom_type not in ["POLYGON", "MULTIPOLYGON"]:
                    errors.append(
                        ValidationErrorItem(
                            code="INVALID_GEOMETRY_TYPE",
                            message=f"Expected polygonal geometry ({expected}), found {geom.geom_type}",
                        )
                    )
            elif geom_type != expected:
                errors.append(
                    ValidationErrorItem(
                        code="INVALID_GEOMETRY_TYPE",
                        message=f"Expected {expected}, found {geom.geom_type}",
                    )
                )

        # Area reasonableness check for cadastral parcels
        if not errors and geom.geom_type in ["Polygon", "MultiPolygon"]:
            area = cls.calculate_geodesic_area(geom)
            if area < 0.1:
                warnings.append(
                    ValidationWarningItem(
                        code="NEGLIGIBLE_AREA",
                        message=f"Calculated geodesic area ({area} m²) is unusually small for a property parcel",
                    )
                )

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    @classmethod
    def check_overlap(
        cls,
        candidate_geom: shapely.Geometry,
        existing_geom: shapely.Geometry,
        min_overlap_area: float = 0.01,
    ) -> Tuple[str, float]:
        """Evaluates spatial intersection between two geometries.
        Distinguishes VALID_SHARED_BOUNDARY (touching at lines/points)
        from INVALID_AREA_OVERLAP (areal intersection > min_overlap_area).

        Returns:
            Tuple of (status, overlap_area_m2)
            Statuses: "DISJOINT", "VALID_SHARED_BOUNDARY", "INVALID_AREA_OVERLAP"
        """
        if candidate_geom.disjoint(existing_geom):
            return ("DISJOINT", 0.0)

        # If they touch only on the boundary
        if candidate_geom.touches(existing_geom):
            return ("VALID_SHARED_BOUNDARY", 0.0)

        # Evaluate intersection geometry
        intersection = candidate_geom.intersection(existing_geom)
        if intersection.is_empty:
            return ("DISJOINT", 0.0)

        # If intersection is 0D or 1D (points or lines)
        if intersection.geom_type in ["Point", "MultiPoint", "LineString", "MultiLineString"]:
            return ("VALID_SHARED_BOUNDARY", 0.0)

        # Areal intersection
        overlap_area = cls.calculate_geodesic_area(intersection)
        if overlap_area > min_overlap_area:
            return ("INVALID_AREA_OVERLAP", overlap_area)
        else:
            return ("VALID_SHARED_BOUNDARY", overlap_area)

    @classmethod
    def check_containment(
        cls,
        inner_geom: shapely.Geometry,
        container_geom: shapely.Geometry,
        tolerance_sq_m: float = 0.1,
    ) -> Tuple[bool, float]:
        """Verifies if inner_geom is contained within container_geom.
        Returns (is_contained, outside_area_m2).
        """
        if container_geom.contains(inner_geom) or container_geom.covers(inner_geom):
            return (True, 0.0)

        # Check difference (portion of inner that lies outside container)
        outside_part = inner_geom.difference(container_geom)
        if outside_part.is_empty:
            return (True, 0.0)

        outside_area = cls.calculate_geodesic_area(outside_part)
        if outside_area <= tolerance_sq_m:
            return (True, outside_area)

        return (False, outside_area)

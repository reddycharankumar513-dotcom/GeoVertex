"""Authoritative 3D geospatial calculations and extrusion engine for GeoVertex Phase 3.

Connects Phase 2 2D PostGIS geometries with vertical metadata (height, base elevation,
vertical datums) to generate 2.5D building extrusion volumes, geodesic cubic volume,
and CesiumJS Cartographic coordinates.
"""
from typing import Any, Dict, List, Optional, Tuple, Union
import shapely.geometry
from shapely import wkt
from app.gis.geometry import GeometryEngine


class Geometry3DEngine:
    """3D geospatial calculations, polyhedral extrusion, and CesiumJS payload generation."""

    @staticmethod
    def calculate_volume_m3(footprint_geom: shapely.geometry.base.BaseGeometry, height: float) -> float:
        """Calculate authoritative volume in cubic meters (m^3) using geodesic base area and height."""
        if height <= 0:
            return 0.0
        area_m2 = GeometryEngine.calculate_geodesic_area(footprint_geom)
        return round(area_m2 * height, 2)

    @staticmethod
    def calculate_3d_bounds(
        footprint_geom: shapely.geometry.base.BaseGeometry,
        base_elevation: float,
        height: float,
    ) -> Tuple[float, float, float, float, float, float]:
        """Compute [min_lon, min_lat, min_alt, max_lon, max_lat, max_alt] 3D bounding box."""
        min_x, min_y, max_x, max_y = footprint_geom.bounds
        min_z = float(base_elevation)
        max_z = float(base_elevation + max(0.0, height))
        return (
            round(min_x, 6),
            round(min_y, 6),
            round(min_z, 2),
            round(max_x, 6),
            round(max_y, 6),
            round(max_z, 2),
        )

    @staticmethod
    def extract_polygon_rings(
        footprint_geom: shapely.geometry.base.BaseGeometry,
    ) -> List[Dict[str, Any]]:
        """Extract exterior and interior hole rings in EPSG:4326 [[lon, lat], ...]."""
        polygons = []
        if footprint_geom.geom_type == 'Polygon':
            polygons.append(footprint_geom)
        elif footprint_geom.geom_type == 'MultiPolygon':
            polygons.extend(footprint_geom.geoms)

        rings_result = []
        for poly in polygons:
            exterior = [[round(p[0], 6), round(p[1], 6)] for p in poly.exterior.coords]
            holes = [[[round(p[0], 6), round(p[1], 6)] for p in hole.coords] for hole in poly.interiors]
            rings_result.append({
                "exterior": exterior,
                "holes": holes,
            })
        return rings_result

    @classmethod
    def generate_cesium_extrusion(
        cls,
        building_id: str,
        building_reference: str,
        building_type: str,
        status: str,
        footprint_geom_input: Union[str, Dict[str, Any], shapely.geometry.base.BaseGeometry],
        height: float,
        height_source: str = "ESTIMATED",
        height_confidence: Optional[float] = None,
        height_unit: str = "METERS",
        base_elevation: float = 0.0,
        elevation_source: str = "LOCAL_REFERENCE_PLANE",
        vertical_reference: str = "METERS_ABOVE_GROUND",
        parcel_id: Optional[str] = None,
        parcel_code: Optional[str] = None,
        source_srid: int = 4326,
    ) -> Dict[str, Any]:
        """Produce a complete, normalized Cesium-compatible 3D extruded building payload."""
        parsed_geom = GeometryEngine.parse_geometry(footprint_geom_input, source_srid=source_srid)
        area_m2 = GeometryEngine.calculate_geodesic_area(parsed_geom)
        centroid_lon, centroid_lat = GeometryEngine.calculate_centroid(parsed_geom)
        volume_m3 = cls.calculate_volume_m3(parsed_geom, height)
        bbox_3d = cls.calculate_3d_bounds(parsed_geom, base_elevation, height)
        rings = cls.extract_polygon_rings(parsed_geom)

        return {
            "building_id": str(building_id),
            "building_reference": building_reference,
            "building_type": building_type,
            "status": status,
            "parcel_id": str(parcel_id) if parcel_id else None,
            "parcel_code": parcel_code,
            "footprint_area_sq_m": area_m2,
            "volume_cu_m": volume_m3,
            "height": round(height, 2),
            "height_source": height_source,
            "height_confidence": height_confidence,
            "height_unit": height_unit,
            "base_elevation": round(base_elevation, 2),
            "elevation_source": elevation_source,
            "vertical_reference": vertical_reference,
            "extruded_height": round(base_elevation + height, 2),
            "centroid": [centroid_lon, centroid_lat, round(base_elevation + (height / 2.0), 2)],
            "bbox_3d": list(bbox_3d),
            "rings": rings,
        }

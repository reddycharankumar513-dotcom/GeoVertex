import math
from typing import Any, Dict, Optional, Tuple
from shapely import wkt
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection
from shapely.ops import transform
import pyproj


class GeometryDiffResult:
    """Encapsulates the deterministic metrics and derived difference geometries."""

    def __init__(
        self,
        baseline_area: float,
        current_area: float,
        area_difference: float,
        area_change_percentage: float,
        intersection_area: float,
        union_area: float,
        iou: float,
        centroid_displacement_m: float,
        boundary_displacement_m: float,
        perimeter_baseline: float,
        perimeter_current: float,
        perimeter_difference: float,
        added_geometry_wkt: Optional[str] = None,
        removed_geometry_wkt: Optional[str] = None,
        symmetric_diff_wkt: Optional[str] = None,
    ):
        self.baseline_area = baseline_area
        self.current_area = current_area
        self.area_difference = area_difference
        self.area_change_percentage = area_change_percentage
        self.intersection_area = intersection_area
        self.union_area = union_area
        self.iou = iou
        self.centroid_displacement_m = centroid_displacement_m
        self.boundary_displacement_m = boundary_displacement_m
        self.perimeter_baseline = perimeter_baseline
        self.perimeter_current = perimeter_current
        self.perimeter_difference = perimeter_difference
        self.added_geometry_wkt = added_geometry_wkt
        self.removed_geometry_wkt = removed_geometry_wkt
        self.symmetric_diff_wkt = symmetric_diff_wkt

    def to_magnitude_dict(self) -> Dict[str, Any]:
        return {
            "baseline_area_sqm": round(self.baseline_area, 2),
            "current_area_sqm": round(self.current_area, 2),
            "area_difference_sqm": round(self.area_difference, 2),
            "area_change_percentage": round(self.area_change_percentage, 2),
            "intersection_area_sqm": round(self.intersection_area, 2),
            "union_area_sqm": round(self.union_area, 2),
            "iou": round(self.iou, 4),
            "centroid_displacement_m": round(self.centroid_displacement_m, 2),
            "boundary_displacement_m": round(self.boundary_displacement_m, 2),
            "perimeter_baseline_m": round(self.perimeter_baseline, 2),
            "perimeter_current_m": round(self.perimeter_current, 2),
            "perimeter_difference_m": round(self.perimeter_difference, 2),
            "added_area_sqm": round(self.area_difference if self.area_difference > 0 else 0.0, 2),
            "removed_area_sqm": round(abs(self.area_difference) if self.area_difference < 0 else 0.0, 2),
        }


class DeterministicGeometryComparator:
    """Computes deterministic spatial metrics and difference polygons between two geometries in EPSG:4326 or UTM."""

    @staticmethod
    def _to_utm(geom: Any) -> Any:
        """Projects geometry from EPSG:4326 to local UTM for accurate metric calculation."""
        if geom is None or geom.is_empty:
            return geom
        centroid = geom.centroid
        lon, lat = centroid.x, centroid.y
        utm_zone = int((lon + 180) / 6) + 1
        is_northern = lat >= 0
        epsg_code = 32600 + utm_zone if is_northern else 32700 + utm_zone

        proj_wgs84 = pyproj.CRS("EPSG:4326")
        proj_utm = pyproj.CRS(f"EPSG:{epsg_code}")
        project_to_utm = pyproj.Transformer.from_crs(proj_wgs84, proj_utm, always_xy=True).transform
        return transform(project_to_utm, geom)

    @staticmethod
    def _from_utm(geom: Any, utm_epsg: int) -> Any:
        """Projects geometry from local UTM back to EPSG:4326."""
        if geom is None or geom.is_empty:
            return geom
        proj_utm = pyproj.CRS(f"EPSG:{utm_epsg}")
        proj_wgs84 = pyproj.CRS("EPSG:4326")
        project_to_wgs84 = pyproj.Transformer.from_crs(proj_utm, proj_wgs84, always_xy=True).transform
        return transform(project_to_wgs84, geom)

    @classmethod
    def compare_geometries(
        cls,
        baseline_wkt: Optional[str],
        current_wkt: Optional[str],
    ) -> GeometryDiffResult:
        """Compares baseline and current WKT geometries deterministically."""
        if not baseline_wkt and not current_wkt:
            return GeometryDiffResult(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

        geom_base_wgs = wkt.loads(baseline_wkt) if baseline_wkt else Polygon()
        geom_curr_wgs = wkt.loads(current_wkt) if current_wkt else Polygon()

        # Handle added (baseline empty)
        if geom_base_wgs.is_empty:
            curr_utm = cls._to_utm(geom_curr_wgs)
            curr_area = float(curr_utm.area)
            return GeometryDiffResult(
                baseline_area=0.0,
                current_area=curr_area,
                area_difference=curr_area,
                area_change_percentage=100.0,
                intersection_area=0.0,
                union_area=curr_area,
                iou=0.0,
                centroid_displacement_m=0.0,
                boundary_displacement_m=0.0,
                perimeter_baseline=0.0,
                perimeter_current=float(curr_utm.length),
                perimeter_difference=float(curr_utm.length),
                added_geometry_wkt=geom_curr_wgs.wkt,
                removed_geometry_wkt=None,
                symmetric_diff_wkt=geom_curr_wgs.wkt,
            )

        # Handle removed (current empty)
        if geom_curr_wgs.is_empty:
            base_utm = cls._to_utm(geom_base_wgs)
            base_area = float(base_utm.area)
            return GeometryDiffResult(
                baseline_area=base_area,
                current_area=0.0,
                area_difference=-base_area,
                area_change_percentage=-100.0,
                intersection_area=0.0,
                union_area=base_area,
                iou=0.0,
                centroid_displacement_m=0.0,
                boundary_displacement_m=0.0,
                perimeter_baseline=float(base_utm.length),
                perimeter_current=0.0,
                perimeter_difference=-float(base_utm.length),
                added_geometry_wkt=None,
                removed_geometry_wkt=geom_base_wgs.wkt,
                symmetric_diff_wkt=geom_base_wgs.wkt,
            )

        # Calculate metrics in UTM metric space
        base_centroid = geom_base_wgs.centroid
        utm_zone = int((base_centroid.x + 180) / 6) + 1
        is_northern = base_centroid.y >= 0
        utm_epsg = 32600 + utm_zone if is_northern else 32700 + utm_zone

        proj_wgs84 = pyproj.CRS("EPSG:4326")
        proj_utm = pyproj.CRS(f"EPSG:{utm_epsg}")
        to_utm_transform = pyproj.Transformer.from_crs(proj_wgs84, proj_utm, always_xy=True).transform
        to_wgs_transform = pyproj.Transformer.from_crs(proj_utm, proj_wgs84, always_xy=True).transform

        base_utm = transform(to_utm_transform, geom_base_wgs)
        curr_utm = transform(to_utm_transform, geom_curr_wgs)

        base_area = float(base_utm.area)
        curr_area = float(curr_utm.area)
        area_diff = curr_area - base_area

        area_pct = (area_diff / base_area * 100.0) if base_area > 0 else 0.0

        intersection_geom = base_utm.intersection(curr_utm)
        union_geom = base_utm.union(curr_utm)

        intersection_area = float(intersection_geom.area) if not intersection_geom.is_empty else 0.0
        union_area = float(union_geom.area) if not union_geom.is_empty else 0.0
        iou = (intersection_area / union_area) if union_area > 0 else 0.0

        # Centroid displacement
        c_base = base_utm.centroid
        c_curr = curr_utm.centroid
        centroid_displacement = math.sqrt((c_curr.x - c_base.x) ** 2 + (c_curr.y - c_base.y) ** 2)

        # Hausdorff boundary displacement
        boundary_displacement = float(base_utm.hausdorff_distance(curr_utm))

        # Perimeters
        base_perim = float(base_utm.length)
        curr_perim = float(curr_utm.length)
        perim_diff = curr_perim - base_perim

        # Derived difference geometries in WGS84
        added_utm = curr_utm.difference(base_utm)
        removed_utm = base_utm.difference(curr_utm)
        sym_utm = curr_utm.symmetric_difference(base_utm)

        if not added_utm.is_empty and added_utm.area < 0.05:
            added_utm = Polygon()
        if not removed_utm.is_empty and removed_utm.area < 0.05:
            removed_utm = Polygon()
        if not sym_utm.is_empty and sym_utm.area < 0.05:
            sym_utm = Polygon()

        added_wgs = transform(to_wgs_transform, added_utm) if not added_utm.is_empty else None
        removed_wgs = transform(to_wgs_transform, removed_utm) if not removed_utm.is_empty else None
        sym_wgs = transform(to_wgs_transform, sym_utm) if not sym_utm.is_empty else None

        return GeometryDiffResult(
            baseline_area=base_area,
            current_area=curr_area,
            area_difference=area_diff,
            area_change_percentage=area_pct,
            intersection_area=intersection_area,
            union_area=union_area,
            iou=iou,
            centroid_displacement_m=centroid_displacement,
            boundary_displacement_m=boundary_displacement,
            perimeter_baseline=base_perim,
            perimeter_current=curr_perim,
            perimeter_difference=perim_diff,
            added_geometry_wkt=added_wgs.wkt if added_wgs else None,
            removed_geometry_wkt=removed_wgs.wkt if removed_wgs else None,
            symmetric_diff_wkt=sym_wgs.wkt if sym_wgs else None,
        )

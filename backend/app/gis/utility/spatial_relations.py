"""Spatial relationship analysis between underground utilities and cadastral parcels or buildings."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import pyproj
from shapely import wkt
from shapely.geometry import base, Point, LineString, Polygon, MultiPolygon
from shapely.ops import transform


def _to_utm(geom: base.BaseGeometry) -> base.BaseGeometry:
    """Project geometry from EPSG:4326 to local UTM for accurate metric calculation."""
    if geom is None or geom.is_empty:
        return geom
    centroid = geom.centroid
    lon, lat = centroid.x, centroid.y
    utm_zone = int((lon + 180) / 6) + 1
    is_northern = lat >= 0
    epsg_code = 32600 + utm_zone if is_northern else 32700 + utm_zone

    proj_wgs84 = pyproj.CRS("EPSG:4326")
    proj_utm = pyproj.CRS(f"EPSG:{epsg_code}")
    project = pyproj.Transformer.from_crs(proj_wgs84, proj_utm, always_xy=True).transform
    return transform(project, geom)


@dataclass
class UtilityParcelRelation:
    parcel_id: str
    parcel_number: str
    intersects: bool
    intersection_length_m: float
    is_crossing: bool
    proximity_m: float
    intersection_wkt: Optional[str] = None
    legal_disclaimer: str = "Purely technical geometric intersection. No easement or legal right is determined."

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parcel_id": self.parcel_id,
            "parcel_number": self.parcel_number,
            "intersects": self.intersects,
            "intersection_length_m": round(self.intersection_length_m, 2),
            "is_crossing": self.is_crossing,
            "proximity_m": round(self.proximity_m, 2),
            "intersection_wkt": self.intersection_wkt,
            "legal_disclaimer": self.legal_disclaimer,
        }


@dataclass
class UtilityBuildingRelation:
    building_id: str
    building_reference: str
    intersects_footprint: bool
    passes_beneath: bool
    enters_building: bool
    intersection_length_m: float
    foundation_proximity_m: float
    vertical_clearance_m: Optional[float]
    relationship_review_required: bool
    technical_disclaimer: str = "Technical geometric relationship only. Does not infer right of access."

    def to_dict(self) -> Dict[str, Any]:
        return {
            "building_id": self.building_id,
            "building_reference": self.building_reference,
            "intersects_footprint": self.intersects_footprint,
            "passes_beneath": self.passes_beneath,
            "enters_building": self.enters_building,
            "intersection_length_m": round(self.intersection_length_m, 2),
            "foundation_proximity_m": round(self.foundation_proximity_m, 2),
            "vertical_clearance_m": round(self.vertical_clearance_m, 2) if self.vertical_clearance_m is not None else None,
            "relationship_review_required": self.relationship_review_required,
            "technical_disclaimer": self.technical_disclaimer,
        }


class UtilitySpatialRelationshipAnalyzer:
    """Analyzes 2D and 3D spatial relationships between utility assets and cadastral entities."""

    @staticmethod
    def analyze_parcel_relationship(
        utility_wkt: str,
        parcel_wkt: str,
        parcel_id: str = "",
        parcel_number: str = "",
    ) -> UtilityParcelRelation:
        """Calculate technical spatial relationship with a cadastral parcel."""
        try:
            util_geom = wkt.loads(utility_wkt)
            parcel_geom = wkt.loads(parcel_wkt)
        except Exception:
            return UtilityParcelRelation(
                parcel_id=parcel_id,
                parcel_number=parcel_number,
                intersects=False,
                intersection_length_m=0.0,
                is_crossing=False,
                proximity_m=999999.0,
            )

        intersects = util_geom.intersects(parcel_geom)
        intersection_wkt = None
        intersection_length = 0.0
        proximity = 0.0
        is_crossing = False

        # Project to UTM for metric distances and lengths
        try:
            util_utm = _to_utm(util_geom)
            parcel_utm = _to_utm(parcel_geom)

            if intersects:
                inter = util_utm.intersection(parcel_utm)
                intersection_length = float(inter.length) if hasattr(inter, "length") else 0.0
                intersection_wkt = inter.wkt

                # Check if it crosses: start or end outside parcel boundary
                if isinstance(util_geom, LineString) and len(util_geom.coords) >= 2:
                    p_start = Point(util_geom.coords[0])
                    p_end = Point(util_geom.coords[-1])
                    start_inside = parcel_geom.contains(p_start)
                    end_inside = parcel_geom.contains(p_end)
                    is_crossing = (not start_inside) or (not end_inside)
            else:
                proximity = float(util_utm.distance(parcel_utm))
        except Exception:
            pass

        return UtilityParcelRelation(
            parcel_id=parcel_id,
            parcel_number=parcel_number,
            intersects=intersects,
            intersection_length_m=intersection_length,
            is_crossing=is_crossing,
            proximity_m=proximity,
            intersection_wkt=intersection_wkt,
        )

    @staticmethod
    def analyze_building_relationship(
        utility_wkt: str,
        building_wkt: str,
        building_id: str = "",
        building_reference: str = "",
        utility_centerline_elev: Optional[float] = None,
        utility_depth: Optional[float] = None,
        building_ground_elev: Optional[float] = None,
        building_basement_depth: Optional[float] = None,
    ) -> UtilityBuildingRelation:
        """Calculate technical spatial relationship with a 3D building footprint."""
        try:
            util_geom = wkt.loads(utility_wkt)
            bld_geom = wkt.loads(building_wkt)
        except Exception:
            return UtilityBuildingRelation(
                building_id=building_id,
                building_reference=building_reference,
                intersects_footprint=False,
                passes_beneath=False,
                enters_building=False,
                intersection_length_m=0.0,
                foundation_proximity_m=999999.0,
                vertical_clearance_m=None,
                relationship_review_required=False,
            )

        intersects = util_geom.intersects(bld_geom)
        intersection_length = 0.0
        proximity = 0.0
        passes_beneath = False
        enters_building = False
        vertical_clearance = None
        review_required = False

        try:
            util_utm = _to_utm(util_geom)
            bld_utm = _to_utm(bld_geom)

            if intersects:
                inter = util_utm.intersection(bld_utm)
                intersection_length = float(inter.length) if hasattr(inter, "length") else 0.0

                # 3D clearance analysis
                if utility_depth is not None and utility_depth > 0.0:
                    basement_d = building_basement_depth or 0.0
                    if utility_depth > basement_d:
                        passes_beneath = True
                        vertical_clearance = utility_depth - basement_d
                    else:
                        enters_building = True
                        review_required = True
                else:
                    # Depth unknown: needs review
                    review_required = True
            else:
                proximity = float(util_utm.distance(bld_utm))
                if proximity < 1.0:
                    review_required = True
        except Exception:
            pass

        return UtilityBuildingRelation(
            building_id=building_id,
            building_reference=building_reference,
            intersects_footprint=intersects,
            passes_beneath=passes_beneath,
            enters_building=enters_building,
            intersection_length_m=intersection_length,
            foundation_proximity_m=proximity,
            vertical_clearance_m=vertical_clearance,
            relationship_review_required=review_required,
        )

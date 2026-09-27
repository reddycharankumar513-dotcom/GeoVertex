"""Deterministic 3D utility clash detection engine with configurable separation rules."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import pyproj
from shapely import wkt
from shapely.geometry import base, Point, LineString
from shapely.ops import transform


def _to_utm(geom: base.BaseGeometry) -> base.BaseGeometry:
    """Project geometry from EPSG:4326 to local UTM for accurate metric distance calculations."""
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
class ClashCandidateResult:
    asset_a_id: str
    asset_b_id: str
    asset_a_ref: str
    asset_b_ref: str
    utility_type_a: str
    utility_type_b: str
    horizontal_relationship: str  # INTERSECTING, NEAR_CROSSING, PARALLEL, DISJOINT
    vertical_relationship: str    # CO_ELEVATION, INSUFFICIENT_CLEARANCE, ADEQUATE_CLEARANCE, UNKNOWN
    measured_horizontal_separation_m: float
    measured_vertical_separation_m: float
    required_horizontal_separation_m: Optional[float]
    required_vertical_separation_m: Optional[float]
    has_configured_rule: bool
    clash_geometry_wkt: Optional[str]
    severity: str                 # CRITICAL, ERROR, WARNING, INFO
    status: str = "OPEN"
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_a_id": self.asset_a_id,
            "asset_b_id": self.asset_b_id,
            "asset_a_ref": self.asset_a_ref,
            "asset_b_ref": self.asset_b_ref,
            "utility_type_a": self.utility_type_a,
            "utility_type_b": self.utility_type_b,
            "horizontal_relationship": self.horizontal_relationship,
            "vertical_relationship": self.vertical_relationship,
            "measured_horizontal_separation_m": round(self.measured_horizontal_separation_m, 2),
            "measured_vertical_separation_m": round(self.measured_vertical_separation_m, 2),
            "required_horizontal_separation_m": self.required_horizontal_separation_m,
            "required_vertical_separation_m": self.required_vertical_separation_m,
            "has_configured_rule": self.has_configured_rule,
            "clash_geometry_wkt": self.clash_geometry_wkt,
            "severity": self.severity,
            "status": self.status,
            "notes": self.notes,
        }


class UtilityClashDetector:
    """Detects 3D spatial clashes between underground utility assets."""

    @staticmethod
    def detect_clash_between_assets(
        asset_a: Dict[str, Any],
        asset_b: Dict[str, Any],
        rules_map: Dict[Tuple[str, str], Dict[str, float]],
        max_search_distance_m: float = 5.0,
    ) -> Optional[ClashCandidateResult]:
        """Evaluate two utility assets for spatial 3D clash/clearance violation."""
        if asset_a["id"] == asset_b["id"]:
            return None

        wkt_a = asset_a.get("geometry_wkt")
        wkt_b = asset_b.get("geometry_wkt")
        if not wkt_a or not wkt_b:
            return None

        try:
            geom_a = wkt.loads(wkt_a)
            geom_b = wkt.loads(wkt_b)
        except Exception:
            return None

        # Bounding box candidate check
        minx_a, miny_a, maxx_a, maxy_a = geom_a.bounds
        minx_b, miny_b, maxx_b, maxy_b = geom_b.bounds

        # Expand bounds slightly (~0.0001 deg ~ 11m)
        buffer_deg = 0.0001
        if (
            maxx_a + buffer_deg < minx_b
            or minx_a - buffer_deg > maxx_b
            or maxy_a + buffer_deg < miny_b
            or miny_a - buffer_deg > maxy_b
        ):
            return None

        # Project to local UTM for precise metric distances
        geom_a_utm = _to_utm(geom_a)
        geom_b_utm = _to_utm(geom_b)

        h_dist = float(geom_a_utm.distance(geom_b_utm))
        if h_dist > max_search_distance_m:
            return None

        # Determine horizontal relationship
        intersects_2d = geom_a_utm.intersects(geom_b_utm)
        clash_wkt = None
        if intersects_2d:
            h_relationship = "INTERSECTING"
            inter_geom = geom_a.intersection(geom_b)
            clash_wkt = inter_geom.wkt
        elif h_dist < 0.5:
            h_relationship = "NEAR_CROSSING"
        elif h_dist < 2.0:
            h_relationship = "PARALLEL"
        else:
            h_relationship = "DISJOINT"

        # Vertical clearance evaluation
        depth_a = asset_a.get("depth")
        depth_b = asset_b.get("depth")
        elev_a = asset_a.get("centerline_elevation")
        elev_b = asset_b.get("centerline_elevation")

        v_dist = 0.0
        v_relationship = "UNKNOWN"

        if elev_a is not None and elev_b is not None:
            v_dist = abs(float(elev_a) - float(elev_b))
            if v_dist < 0.05:
                v_relationship = "CO_ELEVATION"
            else:
                v_relationship = "ELEVATION_OFFSET"
        elif depth_a is not None and depth_b is not None:
            v_dist = abs(float(depth_a) - float(depth_b))
            if v_dist < 0.05:
                v_relationship = "CO_ELEVATION"
            else:
                v_relationship = "ELEVATION_OFFSET"
        else:
            v_dist = 0.0
            v_relationship = "UNKNOWN"

        # Check configured separation rules
        type_a = asset_a.get("utility_type") or asset_a.get("asset_type") or "OTHER"
        type_b = asset_b.get("utility_type") or asset_b.get("asset_type") or "OTHER"
        pair_key = tuple(sorted([type_a, type_b]))

        rule = rules_map.get(pair_key)
        has_rule = rule is not None
        req_h_sep = rule["required_horizontal_separation_m"] if rule else None
        req_v_sep = rule["required_vertical_separation_m"] if rule else None

        severity = "INFO"
        notes = None

        if not has_rule:
            severity = "WARNING" if (intersects_2d and v_dist < 0.3) else "INFO"
            notes = "SEPARATION_RULE_NOT_CONFIGURED: No municipal rule configured for this utility pair."
        else:
            # Rule is configured: evaluate strictly
            h_violation = (h_dist < req_h_sep) if req_h_sep is not None else False
            v_violation = (v_dist < req_v_sep) if req_v_sep is not None else False

            if intersects_2d and v_dist < 0.05:
                severity = "CRITICAL"
                v_relationship = "CO_ELEVATION"
                notes = f"Direct 3D spatial collision: Assets occupy the same vertical depth profile with {h_dist:.2f}m horizontal separation."
            elif h_violation and v_violation:
                severity = "ERROR"
                v_relationship = "INSUFFICIENT_CLEARANCE"
                notes = (
                    f"Separation rule violated: Measured H={h_dist:.2f}m (req {req_h_sep}m), "
                    f"V={v_dist:.2f}m (req {req_v_sep}m)."
                )
            elif h_violation or v_violation:
                severity = "WARNING"
                notes = f"Proximity warning: Measured H={h_dist:.2f}m, V={v_dist:.2f}m."
            else:
                # Meets separation criteria
                return None

        return ClashCandidateResult(
            asset_a_id=str(asset_a["id"]),
            asset_b_id=str(asset_b["id"]),
            asset_a_ref=str(asset_a.get("asset_reference", asset_a["id"])),
            asset_b_ref=str(asset_b.get("asset_reference", asset_b["id"])),
            utility_type_a=type_a,
            utility_type_b=type_b,
            horizontal_relationship=h_relationship,
            vertical_relationship=v_relationship,
            measured_horizontal_separation_m=h_dist,
            measured_vertical_separation_m=v_dist,
            required_horizontal_separation_m=req_h_sep,
            required_vertical_separation_m=req_v_sep,
            has_configured_rule=has_rule,
            clash_geometry_wkt=clash_wkt,
            severity=severity,
            notes=notes,
        )

    @classmethod
    def scan_asset_collection(
        cls,
        assets: List[Dict[str, Any]],
        rules: List[Dict[str, Any]],
    ) -> List[ClashCandidateResult]:
        """Scan a list of assets pairwise with bounding box candidate filtering."""
        rules_map: Dict[Tuple[str, str], Dict[str, float]] = {}
        for r in rules:
            t_a = r.get("utility_type_a", "")
            t_b = r.get("utility_type_b", "")
            pair_key = tuple(sorted([t_a, t_b]))
            rules_map[pair_key] = {
                "required_horizontal_separation_m": float(r.get("required_horizontal_separation_m", 1.0)),
                "required_vertical_separation_m": float(r.get("required_vertical_separation_m", 0.3)),
            }

        clashes: List[ClashCandidateResult] = []
        n = len(assets)
        for i in range(n):
            for j in range(i + 1, n):
                clash = cls.detect_clash_between_assets(assets[i], assets[j], rules_map)
                if clash:
                    clashes.append(clash)

        return clashes

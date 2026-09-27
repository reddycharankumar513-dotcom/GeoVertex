"""Phase 13 — Version Comparison Service.

Computes structured attribute diffs and deterministic geometric variance metrics
between historical entity versions.
"""

import math
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import NotFoundException
from app.models.versioning import EntityVersion
from app.repositories.versioning_repository import entity_version_repository


class VersionComparisonService:
    """Computes field-level and spatial differences between two version records."""

    async def compare_versions(
        self,
        db: AsyncSession,
        version_a_id: uuid.UUID,
        version_b_id: uuid.UUID,
    ) -> Dict[str, Any]:
        v_a = await entity_version_repository.get_by_id(db, version_a_id)
        if not v_a:
            raise NotFoundException(f"Version A ({version_a_id}) not found")

        v_b = await entity_version_repository.get_by_id(db, version_b_id)
        if not v_b:
            raise NotFoundException(f"Version B ({version_b_id}) not found")

        # 1. Attribute / Scalar Field Comparison
        snap_a = v_a.snapshot_data or {}
        snap_b = v_b.snapshot_data or {}

        all_keys = set(snap_a.keys()).union(set(snap_b.keys()))
        modified_fields: Dict[str, Dict[str, Any]] = {}
        added_fields: Dict[str, Any] = {}
        removed_fields: Dict[str, Any] = {}
        unchanged_fields: List[str] = []

        for k in sorted(all_keys):
            if k in snap_a and k in snap_b:
                if snap_a[k] != snap_b[k]:
                    modified_fields[k] = {"before": snap_a[k], "after": snap_b[k]}
                else:
                    unchanged_fields.append(k)
            elif k in snap_b:
                added_fields[k] = snap_b[k]
            else:
                removed_fields[k] = snap_a[k]

        # 2. Geometric Variance Metrics
        metrics_a = v_a.geometry_metrics or {}
        metrics_b = v_b.geometry_metrics or {}

        area_a = float(metrics_a.get("area", 0.0))
        area_b = float(metrics_b.get("area", 0.0))
        area_delta = round(area_b - area_a, 6)
        area_pct = round((area_delta / area_a * 100), 2) if area_a > 0 else 0.0

        perim_a = float(metrics_a.get("length", 0.0))
        perim_b = float(metrics_b.get("length", 0.0))
        perim_delta = round(perim_b - perim_a, 6)

        centroid_a = metrics_a.get("centroid", {})
        centroid_b = metrics_b.get("centroid", {})
        centroid_movement = 0.0
        if centroid_a and centroid_b:
            dx = centroid_b.get("x", 0.0) - centroid_a.get("x", 0.0)
            dy = centroid_b.get("y", 0.0) - centroid_a.get("y", 0.0)
            centroid_movement = round(math.sqrt(dx * dx + dy * dy), 6)

        iou = None
        if v_a.geometry_wkt and v_b.geometry_wkt:
            try:
                from shapely import wkt as shapely_wkt
                g_a = shapely_wkt.loads(v_a.geometry_wkt)
                g_b = shapely_wkt.loads(v_b.geometry_wkt)
                if g_a.is_valid and g_b.is_valid and not g_a.is_empty and not g_b.is_empty:
                    inter_area = g_a.intersection(g_b).area
                    union_area = g_a.union(g_b).area
                    iou = round(float(inter_area / union_area), 4) if union_area > 0 else 0.0
            except Exception:
                iou = None

        geometry_diff = {
            "has_geometry_a": bool(v_a.geometry_wkt),
            "has_geometry_b": bool(v_b.geometry_wkt),
            "geometry_hash_a": v_a.geometry_hash,
            "geometry_hash_b": v_b.geometry_hash,
            "geometry_changed": v_a.geometry_hash != v_b.geometry_hash,
            "area_before": area_a,
            "area_after": area_b,
            "area_delta": area_delta,
            "area_pct_change": area_pct,
            "perimeter_before": perim_a,
            "perimeter_after": perim_b,
            "perimeter_delta": perim_delta,
            "centroid_movement_units": centroid_movement,
            "iou_overlap": iou,
            "bbox_before": metrics_a.get("bounding_box"),
            "bbox_after": metrics_b.get("bounding_box"),
        }

        return {
            "version_a": {
                "id": str(v_a.id),
                "version_number": v_a.version_number,
                "version_status": v_a.version_status,
                "change_type": v_a.change_type,
                "source_type": v_a.source_type,
                "created_at": v_a.created_at.isoformat() if v_a.created_at else None,
                "created_by": str(v_a.created_by) if v_a.created_by else None,
            },
            "version_b": {
                "id": str(v_b.id),
                "version_number": v_b.version_number,
                "version_status": v_b.version_status,
                "change_type": v_b.change_type,
                "source_type": v_b.source_type,
                "created_at": v_b.created_at.isoformat() if v_b.created_at else None,
                "created_by": str(v_b.created_by) if v_b.created_by else None,
            },
            "modified_fields": modified_fields,
            "added_fields": added_fields,
            "removed_fields": removed_fields,
            "unchanged_fields_count": len(unchanged_fields),
            "geometry_diff": geometry_diff,
            "disclaimer": (
                "GeoVertex Technical Version Comparison — Geometric differences are deterministic "
                "technical metrics and do NOT represent legal ownership conclusions or title decisions."
            ),
        }


version_comparison_service = VersionComparisonService()

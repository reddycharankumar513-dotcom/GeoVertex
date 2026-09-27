"""Phase 13 — Entity Versioning Service.

Provides deterministic, immutable snapshotting, geometry hashing, metrics computation,
and atomic version allocation for cadastral and spatial entities.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import logger
from app.models.audit import AuditCategory, AuditSeverity
from app.models.versioning import EntityVersion, VersionStatus, VersionChangeType, VersionSourceType
from app.repositories.audit_repository import audit_repository
from app.repositories.versioning_repository import entity_version_repository


def compute_content_hash(data: Dict[str, Any]) -> str:
    """Computes deterministic SHA-256 hash of canonical JSON data."""
    try:
        canonical_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
    except Exception:
        return hashlib.sha256(str(data).encode("utf-8")).hexdigest()


def compute_geometry_metrics(wkt: Optional[str]) -> Tuple[Dict[str, Any], Optional[str]]:
    """Calculates deterministic spatial metrics (area, perimeter, centroid, bbox, hash).

    Uses shapely when available, with a reliable fallback for lightweight geometries.
    """
    if not wkt:
        return {}, None

    geom_hash = hashlib.sha256(wkt.strip().encode("utf-8")).hexdigest()

    metrics: Dict[str, Any] = {
        "wkt_length": len(wkt),
    }

    try:
        from shapely import wkt as shapely_wkt
        geom = shapely_wkt.loads(wkt)
        metrics["geom_type"] = geom.geom_type
        metrics["area"] = round(float(geom.area), 6)
        metrics["length"] = round(float(geom.length), 6)
        metrics["is_valid"] = bool(geom.is_valid)
        bounds = geom.bounds  # (minx, miny, maxx, maxy)
        metrics["bounding_box"] = {
            "min_x": round(bounds[0], 6),
            "min_y": round(bounds[1], 6),
            "max_x": round(bounds[2], 6),
            "max_y": round(bounds[3], 6),
        }
        centroid = geom.centroid
        metrics["centroid"] = {
            "x": round(float(centroid.x), 6),
            "y": round(float(centroid.y), 6),
        }
    except Exception as e:
        logger.debug(f"[Versioning] Shapely calculation fallback: {e}")
        metrics["geom_type"] = "UNKNOWN"
        metrics["area"] = 0.0
        metrics["length"] = 0.0

    return metrics, geom_hash


class VersioningService:
    """Core service for creating and querying entity version history."""

    async def create_version(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: str,
        snapshot_data: Dict[str, Any],
        geometry_wkt: Optional[str] = None,
        change_type: str = VersionChangeType.UPDATE.value,
        change_reason: Optional[str] = None,
        source_type: str = VersionSourceType.SYSTEM.value,
        source_id: Optional[str] = None,
        actor_user_id: Optional[uuid.UUID] = None,
        workflow_id: Optional[uuid.UUID] = None,
        case_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EntityVersion:
        """Atomically snapshots an entity state into a new immutable EntityVersion."""
        # 1. Determine next version number
        latest = await entity_version_repository.get_latest_version(db, entity_type, entity_id)
        next_version_num = (latest.version_number + 1) if latest else 1
        parent_version_id = latest.id if latest else None

        # 2. Compute hashes and metrics
        content_hash = compute_content_hash(snapshot_data)
        metrics, geom_hash = compute_geometry_metrics(geometry_wkt)

        # 3. Mark previous CURRENT version as SUPERSEDED
        if latest and latest.version_status == VersionStatus.CURRENT.value:
            latest.version_status = VersionStatus.SUPERSEDED.value
            latest.effective_to = datetime.now(timezone.utc)

        # 4. Construct new version record
        new_version_id = uuid.uuid4()
        version = EntityVersion(
            id=new_version_id,
            entity_type=entity_type,
            entity_id=str(entity_id),
            version_number=next_version_num,
            version_uuid=str(uuid.uuid4()),
            version_status=VersionStatus.CURRENT.value,
            created_by=actor_user_id,
            effective_from=datetime.now(timezone.utc),
            change_type=change_type,
            change_reason=change_reason,
            source_type=source_type,
            source_id=source_id,
            parent_version_id=parent_version_id,
            supersedes_version_id=parent_version_id,
            snapshot_data=snapshot_data,
            geometry_wkt=geometry_wkt,
            geometry_type=metrics.get("geom_type"),
            geometry_hash=geom_hash,
            content_hash=content_hash,
            geometry_metrics=metrics,
            workflow_id=workflow_id,
            case_id=case_id,
            correlation_id=correlation_id,
            metadata_json=metadata or {},
        )
        db.add(version)
        await db.flush()

        # Update parent's superseded_by pointer
        if latest:
            latest.superseded_by_version_id = new_version_id
            await db.flush()

        # 5. Log audit event
        await audit_repository.log_event(
            db=db,
            action=f"{entity_type}_VERSION_CREATED",
            category=AuditCategory.PROPERTY.value,
            severity=AuditSeverity.INFO.value,
            entity_type=entity_type,
            entity_id=str(entity_id),
            entity_version_id=new_version_id,
            actor_user_id=actor_user_id,
            workflow_id=workflow_id,
            case_id=case_id,
            correlation_id=correlation_id,
            source_type=source_type,
            source_id=source_id,
            reason=change_reason,
            after_snapshot={"version_number": next_version_num, "change_type": change_type},
            geometry_changed=bool(geometry_wkt),
            details={"version_number": next_version_num, "version_uuid": version.version_uuid},
        )

        logger.info(
            f"[Versioning] Created version v{next_version_num} for {entity_type}:{entity_id}"
        )
        return version

    async def get_version_history(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[EntityVersion], int]:
        return await entity_version_repository.get_versions_for_entity(
            db=db, entity_type=entity_type, entity_id=entity_id, skip=skip, limit=limit
        )

    async def get_version_by_id(
        self, db: AsyncSession, version_id: uuid.UUID
    ) -> Optional[EntityVersion]:
        return await entity_version_repository.get_by_id(db, version_id)

    async def get_version_by_number(
        self, db: AsyncSession, entity_type: str, entity_id: str, version_number: int
    ) -> Optional[EntityVersion]:
        return await entity_version_repository.get_version_by_number(
            db, entity_type, entity_id, version_number
        )

    async def get_active_version(
        self, db: AsyncSession, entity_type: str, entity_id: str
    ) -> Optional[EntityVersion]:
        return await entity_version_repository.get_active_version(db, entity_type, entity_id)


versioning_service = VersioningService()

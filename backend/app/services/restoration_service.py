"""Phase 13 — Controlled Restoration & Rollback Service.

Guarantees history preservation: Rollback creates a NEW version (vN+1) with a
change_type of RESTORATION, never mutating or overwriting historical snapshots.
"""

import uuid
from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import BadRequestException, ForbiddenException, NotFoundException
from app.core.logging import logger
from app.models.audit import AuditCategory, AuditSeverity
from app.models.building import BuildingFootprint
from app.models.floor import Floor
from app.models.parcel import Parcel
from app.models.property import Property
from app.models.unit import PropertyUnit
from app.models.user import User, UserRole
from app.models.versioning import (
    EntityLineage,
    EntityVersion,
    LineageRelationship,
    VersionChangeType,
    VersionSourceType,
    VersionStatus,
)
from app.repositories.audit_repository import audit_repository
from app.repositories.versioning_repository import entity_lineage_repository, entity_version_repository
from app.services.versioning_service import versioning_service


class RestorationService:
    """Orchestrates controlled restoration of cadastral entities from historical snapshots."""

    async def restore_entity_version(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: str,
        target_version_number: int,
        reason: str,
        current_user: User,
        workflow_id: Optional[uuid.UUID] = None,
        case_id: Optional[str] = None,
    ) -> EntityVersion:
        # 1. Authorization check: GOVERNMENT_OFFICER or ADMIN only
        role_str = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
        if role_str not in ["ADMIN", "GOVERNMENT_OFFICER", UserRole.ADMIN.value, UserRole.GOVERNMENT_OFFICER.value]:
            raise ForbiddenException(
                "Restoration restricted to Government Officers and Administrators only."
            )

        # 2. Validation
        if not reason or len(reason.strip()) < 5:
            raise BadRequestException("A valid justification reason (at least 5 characters) is required for restoration.")

        # 3. Locate historical target version
        target_v = await entity_version_repository.get_version_by_number(
            db, entity_type, entity_id, target_version_number
        )
        if not target_v:
            raise NotFoundException(
                f"Version {target_version_number} of {entity_type} {entity_id} does not exist."
            )

        # 4. Get active version for audit before/after
        current_active = await entity_version_repository.get_active_version(db, entity_type, entity_id)

        # 5. Create NEW version (vN+1) holding restored snapshot data
        restored_reason = f"Restored from version {target_version_number}: {reason}"
        new_version = await versioning_service.create_version(
            db=db,
            entity_type=entity_type,
            entity_id=entity_id,
            snapshot_data=target_v.snapshot_data,
            geometry_wkt=target_v.geometry_wkt,
            change_type=VersionChangeType.RESTORATION.value,
            change_reason=restored_reason,
            source_type=VersionSourceType.ADMIN.value if current_user.role == UserRole.ADMIN else VersionSourceType.WORKFLOW.value,
            source_id=f"v{target_version_number}",
            actor_user_id=current_user.id,
            workflow_id=workflow_id,
            case_id=case_id,
            metadata={
                "restored_from_version_number": target_version_number,
                "restored_from_version_id": str(target_v.id),
                "original_change_reason": reason,
            },
        )

        # 6. Apply restored attributes to live database entity
        await self._apply_snapshot_to_live_entity(
            db=db,
            entity_type=entity_type,
            entity_id=entity_id,
            snapshot=target_v.snapshot_data,
            geometry_wkt=target_v.geometry_wkt,
            user_id=current_user.id,
        )

        # 7. Record Lineage entry for Restoration
        lineage = EntityLineage(
            id=uuid.uuid4(),
            source_entity_type=entity_type,
            source_entity_id=entity_id,
            source_version_id=target_v.id,
            target_entity_type=entity_type,
            target_entity_id=entity_id,
            target_version_id=new_version.id,
            relationship_type=LineageRelationship.RESTORATION.value,
            reason=restored_reason,
            actor_user_id=current_user.id,
            workflow_id=workflow_id,
            metadata_json={
                "restored_version_number": target_version_number,
                "new_version_number": new_version.version_number,
            },
        )
        db.add(lineage)
        await db.flush()

        # 8. Log explicit AuditEvent for RESTORATION
        await audit_repository.log_event(
            db=db,
            action=f"{entity_type}_RESTORED",
            category=AuditCategory.GOVERNANCE.value,
            severity=AuditSeverity.WARNING.value,
            entity_type=entity_type,
            entity_id=str(entity_id),
            entity_version_id=new_version.id,
            actor_user_id=current_user.id,
            actor_role=role_str,
            workflow_id=workflow_id,
            case_id=case_id,
            source_type=VersionSourceType.ADMIN.value,
            source_id=f"v{target_version_number}",
            reason=reason,
            before_snapshot={"version_number": current_active.version_number if current_active else None},
            after_snapshot={"version_number": new_version.version_number, "restored_from": target_version_number},
            geometry_changed=bool(target_v.geometry_wkt),
            details={
                "target_version_number": target_version_number,
                "new_version_number": new_version.version_number,
                "justification": reason,
            },
        )

        logger.info(
            f"[Restoration] Entity {entity_type}:{entity_id} restored to v{target_version_number} as v{new_version.version_number}"
        )
        return new_version

    async def _apply_snapshot_to_live_entity(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: str,
        snapshot: Dict[str, Any],
        geometry_wkt: Optional[str],
        user_id: uuid.UUID,
    ) -> None:
        """Applies restored attributes back to the primary operational entity table."""
        u_id = uuid.UUID(entity_id) if isinstance(entity_id, str) else entity_id

        if entity_type == "PARCEL":
            res = await db.execute(select(Parcel).where(Parcel.id == u_id))
            parcel = res.scalars().first()
            if parcel:
                for k, v in snapshot.items():
                    if hasattr(parcel, k) and k not in ["id", "created_at"]:
                        setattr(parcel, k, v)
                if geometry_wkt:
                    parcel.geometry_wkt = geometry_wkt
                parcel.updated_by = user_id
                await db.flush()

        elif entity_type == "PROPERTY":
            res = await db.execute(select(Property).where(Property.id == u_id))
            prop = res.scalars().first()
            if prop:
                for k, v in snapshot.items():
                    if hasattr(prop, k) and k not in ["id", "created_at"]:
                        setattr(prop, k, v)
                prop.updated_by = user_id
                await db.flush()

        elif entity_type in ["BUILDING", "BUILDING_FOOTPRINT"]:
            res = await db.execute(select(BuildingFootprint).where(BuildingFootprint.id == u_id))
            bld = res.scalars().first()
            if bld:
                for k, v in snapshot.items():
                    if hasattr(bld, k) and k not in ["id", "created_at"]:
                        setattr(bld, k, v)
                if geometry_wkt:
                    bld.geometry_wkt = geometry_wkt
                bld.updated_by = user_id
                await db.flush()

        elif entity_type == "FLOOR":
            res = await db.execute(select(Floor).where(Floor.id == u_id))
            fl = res.scalars().first()
            if fl:
                for k, v in snapshot.items():
                    if hasattr(fl, k) and k not in ["id", "created_at"]:
                        setattr(fl, k, v)
                if geometry_wkt:
                    fl.geometry_wkt = geometry_wkt
                fl.updated_by = user_id
                await db.flush()

        elif entity_type in ["UNIT", "PROPERTY_UNIT"]:
            res = await db.execute(select(PropertyUnit).where(PropertyUnit.id == u_id))
            unit = res.scalars().first()
            if unit:
                for k, v in snapshot.items():
                    if hasattr(unit, k) and k not in ["id", "created_at"]:
                        setattr(unit, k, v)
                if geometry_wkt:
                    unit.geometry_wkt = geometry_wkt
                unit.updated_by = user_id
                await db.flush()


restoration_service = RestorationService()

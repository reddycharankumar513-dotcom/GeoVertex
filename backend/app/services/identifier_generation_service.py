"""Phase 12 — Identifier Generation Service.

Implements deterministic generation, hierarchy validation, collision detection,
idempotency, lifecycle management, and bulk generation.

DISCLAIMER: Generates GeoVertex Technical 3D Identifiers — NOT official ULPINs
or legal ownership identifiers.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestException, ConflictException, NotFoundException
from app.core.logging import logger
from app.models.identifier import (
    IdentifierEntityType,
    IdentifierGenerationJob,
    IdentifierLineage,
    IdentifierLineageRelationship,
    IdentifierScheme,
    IdentifierStatus,
    IdentifierType,
    JobStatus,
    PropertyIdentifier,
)
from app.models.building import BuildingFootprint
from app.models.floor import Floor
from app.models.jurisdiction import Jurisdiction
from app.models.parcel import Parcel
from app.models.unit import PropertyUnit
from app.repositories.audit_repository import audit_repository
from app.repositories.identifier_repository import (
    identifier_job_repository,
    identifier_lineage_repository,
    identifier_scheme_repository,
    property_identifier_repository,
)
from app.services.identifier_normalization import (
    assemble_identifier,
    extract_building_component,
    extract_floor_component,
    extract_jurisdiction_component,
    extract_parcel_component,
    extract_unit_component,
    validate_component,
)
from app.services.identifier_qr_service import generate_verification_token


# ─────────────────────────────────────────────────────────────────────────────
# Custom exceptions
# ─────────────────────────────────────────────────────────────────────────────

class IdentifierError(BadRequestException):
    def __init__(self, code: str, message: str, details: Optional[Dict] = None):
        super().__init__(message=message, details={"error_code": code, **(details or {})})
        self.code = code


class IdentifierCollisionError(ConflictException):
    def __init__(self, identifier_value: str):
        super().__init__(
            message=f"Identifier collision detected: '{identifier_value}' already exists for another entity",
            details={"error_code": "IDENTIFIER_COLLISION", "identifier_value": identifier_value},
        )


# ─────────────────────────────────────────────────────────────────────────────
# Hierarchy Loader — validates DB relationships before generation
# ─────────────────────────────────────────────────────────────────────────────

class HierarchyLoader:
    """Loads and validates the full spatial hierarchy from the database."""

    async def load_jurisdiction(self, db: AsyncSession, jur_id: uuid.UUID) -> Jurisdiction:
        result = await db.execute(select(Jurisdiction).where(Jurisdiction.id == jur_id))
        jur = result.scalars().first()
        if not jur:
            raise IdentifierError("IDENTIFIER_INVALID_ENTITY", f"Jurisdiction {jur_id} not found")
        if not jur.is_active:
            raise IdentifierError("IDENTIFIER_INVALID_ENTITY", f"Jurisdiction {jur_id} is inactive")
        return jur

    async def load_parcel(self, db: AsyncSession, parcel_id: uuid.UUID) -> Parcel:
        result = await db.execute(select(Parcel).where(Parcel.id == parcel_id))
        parcel = result.scalars().first()
        if not parcel:
            raise IdentifierError("IDENTIFIER_INVALID_ENTITY", f"Parcel {parcel_id} not found")
        return parcel

    async def load_building(self, db: AsyncSession, building_id: uuid.UUID, parcel_id: Optional[uuid.UUID] = None) -> BuildingFootprint:
        result = await db.execute(select(BuildingFootprint).where(BuildingFootprint.id == building_id))
        building = result.scalars().first()
        if not building:
            raise IdentifierError("IDENTIFIER_INVALID_ENTITY", f"Building {building_id} not found")
        if parcel_id and building.parcel_id and building.parcel_id != parcel_id:
            raise IdentifierError(
                "IDENTIFIER_HIERARCHY_INVALID",
                f"Building {building_id} does not belong to parcel {parcel_id}",
            )
        if not building.parcel_id:
            raise IdentifierError("IDENTIFIER_MISSING_PARENT", f"Building {building_id} has no parcel assignment")
        return building

    async def load_floor(self, db: AsyncSession, floor_id: uuid.UUID, building_id: Optional[uuid.UUID] = None) -> Floor:
        result = await db.execute(select(Floor).where(Floor.id == floor_id))
        floor = result.scalars().first()
        if not floor:
            raise IdentifierError("IDENTIFIER_INVALID_ENTITY", f"Floor {floor_id} not found")
        if building_id and floor.building_id != building_id:
            raise IdentifierError(
                "IDENTIFIER_HIERARCHY_INVALID",
                f"Floor {floor_id} does not belong to building {building_id}",
            )
        return floor

    async def load_unit(self, db: AsyncSession, unit_id: uuid.UUID, floor_id: Optional[uuid.UUID] = None) -> PropertyUnit:
        result = await db.execute(select(PropertyUnit).where(PropertyUnit.id == unit_id))
        unit = result.scalars().first()
        if not unit:
            raise IdentifierError("IDENTIFIER_INVALID_ENTITY", f"Unit {unit_id} not found")
        if floor_id and unit.floor_id != floor_id:
            raise IdentifierError(
                "IDENTIFIER_HIERARCHY_INVALID",
                f"Unit {unit_id} does not belong to floor {floor_id}",
            )
        return unit


loader = HierarchyLoader()


# ─────────────────────────────────────────────────────────────────────────────
# Main Generation Service
# ─────────────────────────────────────────────────────────────────────────────

class IdentifierGenerationService:
    """Core service for deterministic Technical 3D Property Identifier generation."""

    # ── Scheme helpers ──────────────────────────────────────────────────────

    async def get_scheme(
        self,
        db: AsyncSession,
        scheme_id: Optional[uuid.UUID] = None,
        scheme_code: Optional[str] = None,
    ) -> IdentifierScheme:
        if scheme_id:
            scheme = await identifier_scheme_repository.get_by_id(db, scheme_id)
        elif scheme_code:
            scheme = await identifier_scheme_repository.get_by_code(db, scheme_code)
        else:
            scheme = await identifier_scheme_repository.get_active(db)

        if not scheme:
            raise IdentifierError("IDENTIFIER_SCHEME_NOT_FOUND", "No active identifier scheme found")
        if not scheme.active:
            raise IdentifierError("IDENTIFIER_SCHEME_INACTIVE", f"Scheme '{scheme.scheme_code}' is not active")
        return scheme

    # ── Normalization helpers ───────────────────────────────────────────────

    def _normalize_components(
        self,
        scheme: IdentifierScheme,
        jurisdiction: Optional[Jurisdiction] = None,
        parcel: Optional[Parcel] = None,
        building: Optional[BuildingFootprint] = None,
        floor: Optional[Floor] = None,
        unit: Optional[PropertyUnit] = None,
    ) -> Dict[str, Optional[str]]:
        jc = extract_jurisdiction_component(jurisdiction.code, scheme.jurisdiction_component) if jurisdiction else None
        pc = extract_parcel_component(parcel.parcel_code, scheme.parcel_component) if parcel else None
        bc = extract_building_component(building.building_reference, scheme.building_component) if building else None
        fc = extract_floor_component(floor.floor_code, floor.floor_number, scheme.floor_component) if floor else None
        uc = extract_unit_component(unit.unit_code, unit.unit_number, scheme.unit_component) if unit else None
        return {"jc": jc, "pc": pc, "bc": bc, "fc": fc, "uc": uc}

    def _build_identifier_value(
        self,
        scheme: IdentifierScheme,
        components: Dict[str, Optional[str]],
        entity_type: IdentifierEntityType,
    ) -> str:
        """Assemble the identifier string appropriate for the entity level."""
        if entity_type == IdentifierEntityType.JURISDICTION:
            return assemble_identifier(scheme.prefix, scheme.separator, components["jc"])
        elif entity_type == IdentifierEntityType.PARCEL:
            return assemble_identifier(scheme.prefix, scheme.separator, components["jc"], components["pc"])
        elif entity_type == IdentifierEntityType.BUILDING:
            return assemble_identifier(scheme.prefix, scheme.separator, components["jc"], components["pc"], components["bc"])
        elif entity_type == IdentifierEntityType.FLOOR:
            return assemble_identifier(scheme.prefix, scheme.separator, components["jc"], components["pc"], components["bc"], components["fc"])
        else:  # UNIT / PROPERTY_3D_ID
            return assemble_identifier(scheme.prefix, scheme.separator, components["jc"], components["pc"], components["bc"], components["fc"], components["uc"])

    # ── Generate for UNIT (PROPERTY_3D_ID) ──────────────────────────────────

    async def generate_for_unit(
        self,
        db: AsyncSession,
        unit_id: uuid.UUID,
        issued_by: Optional[uuid.UUID] = None,
        scheme_id: Optional[uuid.UUID] = None,
        force_new: bool = False,
    ) -> PropertyIdentifier:
        """Generate or return existing PROPERTY_3D_ID for a unit entity.

        Idempotent: if a valid ACTIVE identifier already exists, returns it.
        force_new=True triggers a new version (supersession).
        """
        scheme = await self.get_scheme(db, scheme_id)

        # Load and validate full hierarchy
        unit = await loader.load_unit(db, unit_id)
        floor = await loader.load_floor(db, unit.floor_id)
        building = await loader.load_building(db, floor.building_id)
        if not building.parcel_id:
            raise IdentifierError("IDENTIFIER_MISSING_PARENT", "Building has no parcel assignment")
        parcel = await loader.load_parcel(db, building.parcel_id)
        jur_result = await db.execute(select(Jurisdiction).where(Jurisdiction.id == parcel.jurisdiction_id))
        jurisdiction = jur_result.scalars().first()
        if not jurisdiction:
            raise IdentifierError("IDENTIFIER_MISSING_PARENT", "Parcel has no jurisdiction")

        # Idempotency check
        if not force_new:
            existing = await property_identifier_repository.get_active_for_entity(
                db, IdentifierEntityType.UNIT.value, str(unit_id), scheme.id
            )
            if existing:
                logger.info(f"Returning existing ACTIVE identifier {existing.identifier_value} for unit {unit_id}")
                return existing

        # Normalize components
        comps = self._normalize_components(scheme, jurisdiction, parcel, building, floor, unit)
        identifier_value = self._build_identifier_value(scheme, comps, IdentifierEntityType.UNIT)

        # Collision detection
        collision = await property_identifier_repository.get_by_value(db, identifier_value)
        if collision:
            if collision.entity_id == str(unit_id):
                # Same entity — idempotent, return it
                return collision
            raise IdentifierCollisionError(identifier_value)

        # Generate verification token
        temp_id = str(uuid.uuid4())
        token = generate_verification_token(temp_id, identifier_value)

        record = PropertyIdentifier(
            id=uuid.UUID(temp_id),
            identifier_value=identifier_value,
            identifier_type=IdentifierType.PROPERTY_3D_ID.value,
            scheme_id=scheme.id,
            entity_type=IdentifierEntityType.UNIT.value,
            entity_id=str(unit_id),
            jurisdiction_id=str(jurisdiction.id),
            parcel_id=str(parcel.id),
            building_id=str(floor.building_id),
            floor_id=str(unit.floor_id),
            unit_id=str(unit_id),
            jurisdiction_component=comps["jc"],
            parcel_component=comps["pc"],
            building_component=comps["bc"],
            floor_component=comps["fc"],
            unit_component=comps["uc"],
            status=IdentifierStatus.ACTIVE.value,
            version=1,
            issued_at=datetime.now(timezone.utc),
            issued_by=str(issued_by) if issued_by else None,
            verification_token=token,
            metadata_json={
                "generated_by": "IdentifierGenerationService",
                "hierarchy": {
                    "jurisdiction_code": jurisdiction.code,
                    "parcel_code": parcel.parcel_code,
                    "building_reference": building.building_reference,
                    "floor_code": floor.floor_code,
                    "unit_code": unit.unit_code,
                },
            },
        )
        db.add(record)
        await db.flush()
        await db.refresh(record)

        await audit_repository.log_event(
            db,
            action="IDENTIFIER_GENERATED",
            entity_type="property_identifier",
            entity_id=str(record.id),
            actor_user_id=issued_by,
            details={
                "identifier_value": identifier_value,
                "entity_type": "UNIT",
                "unit_id": str(unit_id),
                "scheme": scheme.scheme_code,
            },
        )
        logger.info(f"Generated Technical 3D Identifier {identifier_value} for unit {unit_id}")
        return record

    # ── Generate for BUILDING ────────────────────────────────────────────────

    async def generate_for_building(
        self,
        db: AsyncSession,
        building_id: uuid.UUID,
        issued_by: Optional[uuid.UUID] = None,
        scheme_id: Optional[uuid.UUID] = None,
    ) -> PropertyIdentifier:
        scheme = await self.get_scheme(db, scheme_id)
        building = await loader.load_building(db, building_id)
        parcel = await loader.load_parcel(db, building.parcel_id)
        jur_result = await db.execute(select(Jurisdiction).where(Jurisdiction.id == parcel.jurisdiction_id))
        jurisdiction = jur_result.scalars().first()
        if not jurisdiction:
            raise IdentifierError("IDENTIFIER_MISSING_PARENT", "Parcel has no jurisdiction")

        existing = await property_identifier_repository.get_active_for_entity(
            db, IdentifierEntityType.BUILDING.value, str(building_id), scheme.id
        )
        if existing:
            return existing

        comps = self._normalize_components(scheme, jurisdiction, parcel, building)
        identifier_value = self._build_identifier_value(scheme, comps, IdentifierEntityType.BUILDING)

        collision = await property_identifier_repository.get_by_value(db, identifier_value)
        if collision and collision.entity_id != str(building_id):
            raise IdentifierCollisionError(identifier_value)
        if collision:
            return collision

        temp_id = str(uuid.uuid4())
        token = generate_verification_token(temp_id, identifier_value)

        record = PropertyIdentifier(
            id=uuid.UUID(temp_id),
            identifier_value=identifier_value,
            identifier_type=IdentifierType.BUILDING_ID.value,
            scheme_id=scheme.id,
            entity_type=IdentifierEntityType.BUILDING.value,
            entity_id=str(building_id),
            jurisdiction_id=str(jurisdiction.id),
            parcel_id=str(parcel.id),
            building_id=str(building_id),
            jurisdiction_component=comps["jc"],
            parcel_component=comps["pc"],
            building_component=comps["bc"],
            status=IdentifierStatus.ACTIVE.value,
            version=1,
            issued_at=datetime.now(timezone.utc),
            issued_by=str(issued_by) if issued_by else None,
            verification_token=token,
            metadata_json={},
        )
        db.add(record)
        await db.flush()
        await db.refresh(record)

        await audit_repository.log_event(
            db, action="IDENTIFIER_GENERATED", entity_type="property_identifier",
            entity_id=str(record.id), actor_user_id=issued_by,
            details={"identifier_value": identifier_value, "entity_type": "BUILDING"},
        )
        return record

    # ── Generate for PARCEL ──────────────────────────────────────────────────

    async def generate_for_parcel(
        self,
        db: AsyncSession,
        parcel_id: uuid.UUID,
        issued_by: Optional[uuid.UUID] = None,
        scheme_id: Optional[uuid.UUID] = None,
    ) -> PropertyIdentifier:
        scheme = await self.get_scheme(db, scheme_id)
        parcel = await loader.load_parcel(db, parcel_id)
        jur_result = await db.execute(select(Jurisdiction).where(Jurisdiction.id == parcel.jurisdiction_id))
        jurisdiction = jur_result.scalars().first()
        if not jurisdiction:
            raise IdentifierError("IDENTIFIER_MISSING_PARENT", "Parcel has no jurisdiction")

        existing = await property_identifier_repository.get_active_for_entity(
            db, IdentifierEntityType.PARCEL.value, str(parcel_id), scheme.id
        )
        if existing:
            return existing

        comps = self._normalize_components(scheme, jurisdiction, parcel)
        identifier_value = self._build_identifier_value(scheme, comps, IdentifierEntityType.PARCEL)

        collision = await property_identifier_repository.get_by_value(db, identifier_value)
        if collision and collision.entity_id != str(parcel_id):
            raise IdentifierCollisionError(identifier_value)
        if collision:
            return collision

        temp_id = str(uuid.uuid4())
        token = generate_verification_token(temp_id, identifier_value)

        record = PropertyIdentifier(
            id=uuid.UUID(temp_id),
            identifier_value=identifier_value,
            identifier_type=IdentifierType.PARCEL_ID.value,
            scheme_id=scheme.id,
            entity_type=IdentifierEntityType.PARCEL.value,
            entity_id=str(parcel_id),
            jurisdiction_id=str(jurisdiction.id),
            parcel_id=str(parcel_id),
            jurisdiction_component=comps["jc"],
            parcel_component=comps["pc"],
            status=IdentifierStatus.ACTIVE.value,
            version=1,
            issued_at=datetime.now(timezone.utc),
            issued_by=str(issued_by) if issued_by else None,
            verification_token=token,
            metadata_json={},
        )
        db.add(record)
        await db.flush()
        await db.refresh(record)

        await audit_repository.log_event(
            db, action="IDENTIFIER_GENERATED", entity_type="property_identifier",
            entity_id=str(record.id), actor_user_id=issued_by,
            details={"identifier_value": identifier_value, "entity_type": "PARCEL"},
        )
        return record

    # ── Generate for FLOOR ───────────────────────────────────────────────────

    async def generate_for_floor(
        self,
        db: AsyncSession,
        floor_id: uuid.UUID,
        issued_by: Optional[uuid.UUID] = None,
        scheme_id: Optional[uuid.UUID] = None,
    ) -> PropertyIdentifier:
        scheme = await self.get_scheme(db, scheme_id)
        floor = await loader.load_floor(db, floor_id)
        building = await loader.load_building(db, floor.building_id)
        parcel = await loader.load_parcel(db, building.parcel_id)
        jur_result = await db.execute(select(Jurisdiction).where(Jurisdiction.id == parcel.jurisdiction_id))
        jurisdiction = jur_result.scalars().first()

        existing = await property_identifier_repository.get_active_for_entity(
            db, IdentifierEntityType.FLOOR.value, str(floor_id), scheme.id
        )
        if existing:
            return existing

        comps = self._normalize_components(scheme, jurisdiction, parcel, building, floor)
        identifier_value = self._build_identifier_value(scheme, comps, IdentifierEntityType.FLOOR)

        collision = await property_identifier_repository.get_by_value(db, identifier_value)
        if collision and collision.entity_id != str(floor_id):
            raise IdentifierCollisionError(identifier_value)
        if collision:
            return collision

        temp_id = str(uuid.uuid4())
        token = generate_verification_token(temp_id, identifier_value)

        record = PropertyIdentifier(
            id=uuid.UUID(temp_id),
            identifier_value=identifier_value,
            identifier_type=IdentifierType.FLOOR_ID.value,
            scheme_id=scheme.id,
            entity_type=IdentifierEntityType.FLOOR.value,
            entity_id=str(floor_id),
            jurisdiction_id=str(jurisdiction.id) if jurisdiction else None,
            parcel_id=str(parcel.id),
            building_id=str(building.id),
            floor_id=str(floor_id),
            jurisdiction_component=comps["jc"],
            parcel_component=comps["pc"],
            building_component=comps["bc"],
            floor_component=comps["fc"],
            status=IdentifierStatus.ACTIVE.value,
            version=1,
            issued_at=datetime.now(timezone.utc),
            issued_by=str(issued_by) if issued_by else None,
            verification_token=token,
            metadata_json={},
        )
        db.add(record)
        await db.flush()
        await db.refresh(record)

        await audit_repository.log_event(
            db, action="IDENTIFIER_GENERATED", entity_type="property_identifier",
            entity_id=str(record.id), actor_user_id=issued_by,
            details={"identifier_value": identifier_value, "entity_type": "FLOOR"},
        )
        return record

    # ── Preview (no persist) ────────────────────────────────────────────────

    async def preview_for_unit(
        self,
        db: AsyncSession,
        unit_id: uuid.UUID,
        scheme_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Preview what identifier would be generated — does NOT persist."""
        scheme = await self.get_scheme(db, scheme_id)
        try:
            unit = await loader.load_unit(db, unit_id)
            floor = await loader.load_floor(db, unit.floor_id)
            building = await loader.load_building(db, floor.building_id)
            parcel = await loader.load_parcel(db, building.parcel_id)
            jur_result = await db.execute(select(Jurisdiction).where(Jurisdiction.id == parcel.jurisdiction_id))
            jurisdiction = jur_result.scalars().first()

            comps = self._normalize_components(scheme, jurisdiction, parcel, building, floor, unit)
            identifier_value = self._build_identifier_value(scheme, comps, IdentifierEntityType.UNIT)
            collision = await property_identifier_repository.get_by_value(db, identifier_value)

            existing = await property_identifier_repository.get_active_for_entity(
                db, IdentifierEntityType.UNIT.value, str(unit_id), scheme.id
            )

            return {
                "eligible": True,
                "already_assigned": existing is not None,
                "collision": collision is not None and (not existing or collision.id != existing.id),
                "preview_identifier": identifier_value,
                "scheme_code": scheme.scheme_code,
                "components": {
                    "jurisdiction": comps["jc"],
                    "parcel": comps["pc"],
                    "building": comps["bc"],
                    "floor": comps["fc"],
                    "unit": comps["uc"],
                },
                "hierarchy": {
                    "jurisdiction_code": jurisdiction.code if jurisdiction else None,
                    "parcel_code": parcel.parcel_code,
                    "building_reference": building.building_reference,
                    "floor_code": floor.floor_code,
                    "unit_code": unit.unit_code,
                },
                "errors": [],
            }
        except IdentifierError as e:
            return {
                "eligible": False,
                "already_assigned": False,
                "collision": False,
                "preview_identifier": None,
                "scheme_code": scheme.scheme_code,
                "components": {},
                "hierarchy": {},
                "errors": [e.message],
            }

    # ── Lifecycle: Supersede ────────────────────────────────────────────────

    async def supersede(
        self,
        db: AsyncSession,
        identifier_id: uuid.UUID,
        reason: str,
        actor_id: uuid.UUID,
        new_entity_id: Optional[str] = None,
    ) -> Tuple[PropertyIdentifier, PropertyIdentifier]:
        """Supersede an existing identifier, creating a new one in its place."""
        old = await property_identifier_repository.get_by_id(db, identifier_id)
        if not old:
            raise NotFoundException(f"Identifier {identifier_id} not found")
        if old.status != IdentifierStatus.ACTIVE.value:
            raise IdentifierError(
                "IDENTIFIER_NOT_ACTIVE",
                f"Only ACTIVE identifiers can be superseded (current: {old.status})",
            )

        entity_type = IdentifierEntityType(old.entity_type)
        target_entity_id = uuid.UUID(new_entity_id or old.entity_id)

        # Generate new identifier
        if entity_type == IdentifierEntityType.UNIT:
            new_record = await self.generate_for_unit(db, target_entity_id, actor_id, old.scheme_id, force_new=True)
        elif entity_type == IdentifierEntityType.BUILDING:
            new_record = await self.generate_for_building(db, target_entity_id, actor_id, old.scheme_id)
        elif entity_type == IdentifierEntityType.PARCEL:
            new_record = await self.generate_for_parcel(db, target_entity_id, actor_id, old.scheme_id)
        elif entity_type == IdentifierEntityType.FLOOR:
            new_record = await self.generate_for_floor(db, target_entity_id, actor_id, old.scheme_id)
        else:
            raise IdentifierError("IDENTIFIER_INVALID_ENTITY", f"Supersession not supported for {entity_type}")

        # Update old record
        old.status = IdentifierStatus.SUPERSEDED.value
        old.superseded_by_identifier_id = str(new_record.id)
        await db.flush()

        # Update new record's back-pointer
        new_record.supersedes_identifier_id = str(old.id)
        await db.flush()

        # Create lineage record
        lineage = IdentifierLineage(
            source_identifier_id=str(old.id),
            target_identifier_id=str(new_record.id),
            relationship_type=IdentifierLineageRelationship.REPLACEMENT.value,
            reason=reason,
            effective_date=datetime.now(timezone.utc),
            created_by=str(actor_id),
        )
        db.add(lineage)
        await db.flush()

        await audit_repository.log_event(
            db, action="IDENTIFIER_SUPERSEDED", entity_type="property_identifier",
            entity_id=str(old.id), actor_user_id=actor_id,
            details={"old_value": old.identifier_value, "new_value": new_record.identifier_value, "reason": reason},
        )
        return old, new_record

    # ── Lifecycle: Retire ───────────────────────────────────────────────────

    async def retire(
        self,
        db: AsyncSession,
        identifier_id: uuid.UUID,
        reason: str,
        actor_id: uuid.UUID,
    ) -> PropertyIdentifier:
        record = await property_identifier_repository.get_by_id(db, identifier_id)
        if not record:
            raise NotFoundException(f"Identifier {identifier_id} not found")
        if record.status not in (IdentifierStatus.ACTIVE.value, IdentifierStatus.SUSPENDED.value):
            raise IdentifierError("IDENTIFIER_INVALID_STATE", f"Cannot retire identifier in state: {record.status}")
        record.status = IdentifierStatus.RETIRED.value
        record.notes = f"Retired: {reason}"
        await db.flush()
        await audit_repository.log_event(
            db, action="IDENTIFIER_RETIRED", entity_type="property_identifier",
            entity_id=str(identifier_id), actor_user_id=actor_id,
            details={"reason": reason},
        )
        return record

    # ── Lifecycle: Revoke ───────────────────────────────────────────────────

    async def revoke(
        self,
        db: AsyncSession,
        identifier_id: uuid.UUID,
        reason: str,
        actor_id: uuid.UUID,
    ) -> PropertyIdentifier:
        record = await property_identifier_repository.get_by_id(db, identifier_id)
        if not record:
            raise NotFoundException(f"Identifier {identifier_id} not found")
        record.status = IdentifierStatus.REVOKED.value
        record.notes = f"Revoked: {reason}"
        await db.flush()
        await audit_repository.log_event(
            db, action="IDENTIFIER_REVOKED", entity_type="property_identifier",
            entity_id=str(identifier_id), actor_user_id=actor_id,
            details={"reason": reason},
        )
        return record

    # ── Bulk Preview ────────────────────────────────────────────────────────

    async def bulk_preview_building(
        self,
        db: AsyncSession,
        building_id: uuid.UUID,
        scheme_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Preview bulk generation for all units in a building."""
        scheme = await self.get_scheme(db, scheme_id)
        units_result = await db.execute(
            select(PropertyUnit).where(PropertyUnit.building_id == building_id)
        )
        units = list(units_result.scalars().all())

        total = len(units)
        already_assigned = 0
        eligible = 0
        blocked = 0
        collisions = 0
        previews = []

        for unit in units:
            preview = await self.preview_for_unit(db, unit.id, scheme.id)
            if preview["already_assigned"]:
                already_assigned += 1
            elif preview["collision"]:
                collisions += 1
            elif not preview["eligible"]:
                blocked += 1
            else:
                eligible += 1
            previews.append({
                "unit_id": str(unit.id),
                "unit_code": unit.unit_code,
                **preview,
            })

        return {
            "scope": {"building_id": str(building_id), "scheme_code": scheme.scheme_code},
            "total": total,
            "already_assigned": already_assigned,
            "eligible": eligible,
            "blocked": blocked,
            "collisions": collisions,
            "ready_to_generate": eligible,
            "previews": previews[:20],  # Cap preview list for response size
        }

    # ── Bulk Generate (synchronous — for small batches) ─────────────────────

    async def bulk_generate_building(
        self,
        db: AsyncSession,
        building_id: uuid.UUID,
        actor_id: uuid.UUID,
        scheme_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Bulk generate identifiers for all eligible units in a building."""
        scheme = await self.get_scheme(db, scheme_id)

        # Create job record
        job = IdentifierGenerationJob(
            scheme_id=scheme.id,
            scope={"building_id": str(building_id), "entity_type": "UNIT"},
            requested_by=str(actor_id),
            status=JobStatus.RUNNING.value,
            started_at=datetime.now(timezone.utc),
        )
        db.add(job)
        await db.flush()
        await db.refresh(job)

        units_result = await db.execute(
            select(PropertyUnit).where(PropertyUnit.building_id == building_id)
        )
        units = list(units_result.scalars().all())
        job.total = len(units)

        generated = []
        errors = []
        for unit in units:
            try:
                record = await self.generate_for_unit(db, unit.id, actor_id, scheme.id)
                job.generated += 1
                generated.append({"unit_id": str(unit.id), "identifier": record.identifier_value, "status": record.status})
            except IdentifierCollisionError as e:
                job.conflicts += 1
                errors.append({"unit_id": str(unit.id), "error": "COLLISION", "detail": str(e.message)})
            except IdentifierError as e:
                job.blocked += 1
                errors.append({"unit_id": str(unit.id), "error": e.code, "detail": e.message})

        job.status = JobStatus.COMPLETED.value
        job.completed_at = datetime.now(timezone.utc)
        job.result_summary = {"generated": generated[:50], "errors": errors[:50]}
        await db.flush()

        await audit_repository.log_event(
            db, action="BULK_IDENTIFIER_GENERATED", entity_type="identifier_generation_job",
            entity_id=str(job.id), actor_user_id=actor_id,
            details={"building_id": str(building_id), "generated": job.generated, "blocked": job.blocked},
        )
        return {
            "job_id": str(job.id),
            "status": job.status,
            "total": job.total,
            "generated": job.generated,
            "blocked": job.blocked,
            "conflicts": job.conflicts,
            "results": generated,
            "errors": errors,
        }


identifier_generation_service = IdentifierGenerationService()

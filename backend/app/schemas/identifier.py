"""Phase 12 — Pydantic schemas for Technical 3D Property Identifier Engine API."""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Scheme Schemas
# ─────────────────────────────────────────────────────────────────────────────

class IdentifierSchemeBase(BaseModel):
    scheme_code: str = Field(..., max_length=64, description="Unique scheme code, e.g. GV3D-V1")
    name: str = Field(..., max_length=255)
    version: int = Field(1, ge=1)
    description: Optional[str] = None
    prefix: str = Field("GV", max_length=16)
    separator: str = Field("-", max_length=4)
    jurisdiction_component: str = Field("strip_prefix_code", max_length=128)
    parcel_component: str = Field("strip_prefix_code", max_length=128)
    building_component: str = Field("strip_prefix_ref", max_length=128)
    floor_component: str = Field("strip_floor_suffix", max_length=128)
    unit_component: str = Field("strip_unit_suffix", max_length=128)
    padding_rules: Dict[str, Any] = Field(default_factory=dict)
    checksum_enabled: bool = False
    active: bool = True
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None


class IdentifierSchemeCreate(IdentifierSchemeBase):
    pass


class IdentifierSchemePatch(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None


class IdentifierSchemeResponse(IdentifierSchemeBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Identifier Schemas
# ─────────────────────────────────────────────────────────────────────────────

class IdentifierHierarchy(BaseModel):
    jurisdiction_id: Optional[str] = None
    jurisdiction_component: Optional[str] = None
    parcel_id: Optional[str] = None
    parcel_component: Optional[str] = None
    building_id: Optional[str] = None
    building_component: Optional[str] = None
    floor_id: Optional[str] = None
    floor_component: Optional[str] = None
    unit_id: Optional[str] = None
    unit_component: Optional[str] = None


class PropertyIdentifierResponse(BaseModel):
    id: uuid.UUID
    identifier_value: str = Field(..., description="GeoVertex Technical 3D Identifier (NOT an official ULPIN)")
    identifier_type: str
    scheme_id: uuid.UUID
    scheme_code: Optional[str] = None
    entity_type: str
    entity_id: str
    status: str
    version: int
    issued_at: Optional[datetime] = None
    issued_by: Optional[str] = None
    supersedes_identifier_id: Optional[str] = None
    superseded_by_identifier_id: Optional[str] = None
    verification_token: Optional[str] = None
    hierarchy: Optional[IdentifierHierarchy] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_hierarchy(cls, record: Any, scheme_code: Optional[str] = None) -> "PropertyIdentifierResponse":
        return cls(
            id=record.id,
            identifier_value=record.identifier_value,
            identifier_type=record.identifier_type,
            scheme_id=record.scheme_id,
            scheme_code=scheme_code,
            entity_type=record.entity_type,
            entity_id=record.entity_id,
            status=record.status,
            version=record.version,
            issued_at=record.issued_at,
            issued_by=record.issued_by,
            supersedes_identifier_id=record.supersedes_identifier_id,
            superseded_by_identifier_id=record.superseded_by_identifier_id,
            verification_token=record.verification_token,
            hierarchy=IdentifierHierarchy(
                jurisdiction_id=record.jurisdiction_id,
                jurisdiction_component=record.jurisdiction_component,
                parcel_id=record.parcel_id,
                parcel_component=record.parcel_component,
                building_id=record.building_id,
                building_component=record.building_component,
                floor_id=record.floor_id,
                floor_component=record.floor_component,
                unit_id=record.unit_id,
                unit_component=record.unit_component,
            ),
            notes=record.notes,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Generation Request Schemas
# ─────────────────────────────────────────────────────────────────────────────

class GenerateIdentifierRequest(BaseModel):
    entity_type: str = Field(..., description="PARCEL | BUILDING | FLOOR | UNIT")
    entity_id: uuid.UUID = Field(..., description="UUID of the spatial entity")
    scheme_id: Optional[uuid.UUID] = None
    force_new: bool = Field(False, description="Force new version (triggers supersession)")


class PreviewIdentifierRequest(BaseModel):
    entity_type: str = Field(..., description="PARCEL | BUILDING | FLOOR | UNIT")
    entity_id: uuid.UUID
    scheme_id: Optional[uuid.UUID] = None


class PreviewIdentifierResponse(BaseModel):
    eligible: bool
    already_assigned: bool
    collision: bool
    preview_identifier: Optional[str] = None
    scheme_code: Optional[str] = None
    components: Dict[str, Optional[str]] = Field(default_factory=dict)
    hierarchy: Dict[str, Optional[str]] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Lifecycle Action Schemas
# ─────────────────────────────────────────────────────────────────────────────

class SupersedeRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=1024)
    new_entity_id: Optional[str] = Field(None, description="Optional: redirect to different entity UUID")


class RetireRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=1024)


class RevokeRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=1024)


class SupersedeResponse(BaseModel):
    old_identifier: PropertyIdentifierResponse
    new_identifier: PropertyIdentifierResponse
    message: str = "Identifier superseded successfully"


# ─────────────────────────────────────────────────────────────────────────────
# Verification Schemas
# ─────────────────────────────────────────────────────────────────────────────

class VerificationResult(BaseModel):
    """Public verification response — no sensitive data exposed."""
    valid: bool
    identifier_value: Optional[str] = None
    identifier_type: Optional[str] = None
    status: Optional[str] = None
    entity_type: Optional[str] = None
    scheme_code: Optional[str] = None
    issued_at: Optional[datetime] = None
    hierarchy: Optional[IdentifierHierarchy] = None
    verification_message: str
    disclaimer: str = (
        "This is a GeoVertex Technical 3D Identifier. It is NOT an official ULPIN, "
        "legal ownership identifier, or government cadastral registration number."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Lineage Schemas
# ─────────────────────────────────────────────────────────────────────────────

class IdentifierLineageResponse(BaseModel):
    id: uuid.UUID
    source_identifier_id: str
    target_identifier_id: str
    relationship_type: str
    reason: Optional[str] = None
    effective_date: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Bulk Generation Schemas
# ─────────────────────────────────────────────────────────────────────────────

class BulkGenerateRequest(BaseModel):
    entity_type: str = Field("UNIT", description="Currently supports UNIT bulk generation per building")
    building_id: uuid.UUID = Field(..., description="Generate identifiers for all eligible units in this building")
    scheme_id: Optional[uuid.UUID] = None
    confirmed: bool = Field(False, description="Must be true to proceed with generation")


class BulkPreviewRequest(BaseModel):
    entity_type: str = Field("UNIT")
    building_id: uuid.UUID
    scheme_id: Optional[uuid.UUID] = None


class BulkGenerateResponse(BaseModel):
    job_id: Optional[str] = None
    status: str
    total: int
    generated: int
    blocked: int
    conflicts: int
    results: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[Dict[str, Any]] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Statistics / Dashboard Schemas
# ─────────────────────────────────────────────────────────────────────────────

class IdentifierStatisticsResponse(BaseModel):
    total: int
    by_status: Dict[str, int]
    by_entity_type: Dict[str, int]
    active: int
    superseded: int
    retired: int
    revoked: int
    draft: int


# ─────────────────────────────────────────────────────────────────────────────
# Job Schemas
# ─────────────────────────────────────────────────────────────────────────────

class IdentifierJobResponse(BaseModel):
    id: uuid.UUID
    scheme_id: uuid.UUID
    scope: Dict[str, Any]
    requested_by: Optional[str] = None
    status: str
    total: int
    eligible: int
    generated: int
    blocked: int
    conflicts: int
    skipped: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

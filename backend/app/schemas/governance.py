"""Phase 13 — Governance, Versioning, and Audit Schemas."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────
# Audit Schemas
# ──────────────────────────────────────────────────

class AuditEventResponse(BaseModel):
    id: uuid.UUID
    event_id: Optional[str] = None
    timestamp: datetime
    action: str
    category: str
    severity: str
    result: str
    entity_type: str
    entity_id: str
    entity_version_id: Optional[uuid.UUID] = None
    actor_user_id: Optional[uuid.UUID] = None
    actor_role: Optional[str] = None
    organization_id: Optional[uuid.UUID] = None
    jurisdiction_id: Optional[uuid.UUID] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    workflow_id: Optional[uuid.UUID] = None
    case_id: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    before_snapshot: Optional[Dict[str, Any]] = Field(default_factory=dict)
    after_snapshot: Optional[Dict[str, Any]] = Field(default_factory=dict)
    changed_fields: Optional[List[str]] = Field(default_factory=list)
    geometry_changed: Optional[bool] = False
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[Dict[str, Any]] = Field(default_factory=dict)

    model_config = {"from_attributes": True}

    @classmethod
    def model_validate(cls, obj: Any, **kwargs) -> "AuditEventResponse":
        # Normalize None values from historical database rows
        if hasattr(obj, "before_snapshot") and obj.before_snapshot is None:
            obj.before_snapshot = {}
        if hasattr(obj, "after_snapshot") and obj.after_snapshot is None:
            obj.after_snapshot = {}
        if hasattr(obj, "changed_fields") and obj.changed_fields is None:
            obj.changed_fields = []
        if hasattr(obj, "details") and obj.details is None:
            obj.details = {}
        if hasattr(obj, "geometry_changed") and obj.geometry_changed is None:
            obj.geometry_changed = False
        return super().model_validate(obj, **kwargs)


class AuditStatisticsResponse(BaseModel):
    total_events: int
    by_category: Dict[str, int]
    by_severity: Dict[str, int]
    by_result: Dict[str, int]
    distinct_actors: int


# ──────────────────────────────────────────────────
# Versioning Schemas
# ──────────────────────────────────────────────────

class EntityVersionResponse(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: str
    version_number: int
    version_uuid: str
    version_status: str
    created_by: Optional[uuid.UUID] = None
    effective_from: datetime
    effective_to: Optional[datetime] = None
    change_type: str
    change_reason: Optional[str] = None
    source_type: str
    source_id: Optional[str] = None
    parent_version_id: Optional[uuid.UUID] = None
    supersedes_version_id: Optional[uuid.UUID] = None
    superseded_by_version_id: Optional[uuid.UUID] = None
    snapshot_data: Dict[str, Any]
    geometry_wkt: Optional[str] = None
    geometry_srid: Optional[int] = 4326
    geometry_type: Optional[str] = None
    geometry_hash: Optional[str] = None
    content_hash: Optional[str] = None
    geometry_metrics: Dict[str, Any] = Field(default_factory=dict)
    workflow_id: Optional[uuid.UUID] = None
    case_id: Optional[str] = None
    correlation_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class VersionComparisonResponse(BaseModel):
    version_a: Dict[str, Any]
    version_b: Dict[str, Any]
    modified_fields: Dict[str, Dict[str, Any]]
    added_fields: Dict[str, Any]
    removed_fields: Dict[str, Any]
    unchanged_fields_count: int
    geometry_diff: Dict[str, Any]
    disclaimer: str


class RestoreVersionRequest(BaseModel):
    target_version_number: int = Field(..., ge=1, description="Version number to restore from")
    reason: str = Field(..., min_length=5, description="Mandatory justification reason for restoration")
    workflow_id: Optional[uuid.UUID] = None
    case_id: Optional[str] = None


class EntityLineageResponse(BaseModel):
    id: uuid.UUID
    source_entity_type: str
    source_entity_id: str
    source_version_id: Optional[uuid.UUID] = None
    target_entity_type: str
    target_entity_id: str
    target_version_id: Optional[uuid.UUID] = None
    relationship_type: str
    reason: Optional[str] = None
    actor_user_id: Optional[uuid.UUID] = None
    workflow_id: Optional[uuid.UUID] = None
    created_at: datetime
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────
# Notification Schemas
# ──────────────────────────────────────────────────

class NotificationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    notification_type: str
    title: str
    message: str
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    delivery_channel: str
    status: str
    severity: str
    organization_id: Optional[uuid.UUID] = None
    jurisdiction_id: Optional[uuid.UUID] = None
    workflow_id: Optional[uuid.UUID] = None
    case_id: Optional[str] = None
    correlation_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationPreferenceResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    notification_type: str
    channel: str
    enabled: bool
    digest_frequency: str

    model_config = {"from_attributes": True}


class NotificationPreferenceUpdate(BaseModel):
    notification_type: str
    channel: str = "IN_APP"
    enabled: bool
    digest_frequency: str = "IMMEDIATE"


class TestNotificationRequest(BaseModel):
    notification_type: str = "SYSTEM_ALERT"
    title: str = "Test System Alert"
    message: str = "This is an administrative test notification."
    severity: str = "INFO"
    channel: str = "IN_APP"


# ──────────────────────────────────────────────────
# Governance Schemas
# ──────────────────────────────────────────────────

class GovernanceDashboardResponse(BaseModel):
    audit: Dict[str, Any]
    versioning: Dict[str, Any]
    notifications: Dict[str, Any]
    recent_events: List[Dict[str, Any]]


class DataIntegrityResponse(BaseModel):
    status: str
    issues_count: int
    issues: List[str]
    disclaimer: str

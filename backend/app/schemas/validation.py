import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ValidationRunCreateRequest(BaseModel):
    """Request payload to initiate a topology validation run."""
    target_type: str = Field(
        ...,
        description="Target scope: PARCEL, BUILDING, FLOOR, UNIT, AI_RESULT, SURVEY_SUBMISSION, JURISDICTION, SYSTEM",
    )
    target_id: Optional[str] = Field(
        None,
        description="Target entity UUID or code. Nullable for systemic or jurisdictional runs.",
    )
    validation_type: Optional[str] = Field(
        "SINGLE_ENTITY",
        description="Validation type: SINGLE_ENTITY, PARCEL, BUILDING, FLOOR, UNIT, AI_CANDIDATE, SURVEY_SUBMISSION, CROSS_DATASET, JURISDICTION, SYSTEM",
    )
    rules_filter: Optional[List[str]] = Field(
        None,
        description="Optional subset of specific rule IDs to execute.",
    )
    tolerance_overrides: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional numerical tolerance overrides for this run.",
    )
    geometry_wkt: Optional[str] = Field(
        None,
        description="Optional ad-hoc WKT geometry string to validate directly.",
    )


class ValidationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    validation_type: str
    target_type: str
    target_id: Optional[str]
    status: str
    stage: str
    requested_by: Optional[uuid.UUID]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_ms: Optional[int]
    ruleset_version: str
    parameters: Dict[str, Any]
    summary: Dict[str, Any]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime


class ValidationIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    validation_run_id: uuid.UUID
    rule_id: str
    rule_version: str
    issue_code: str
    category: str
    severity: str
    status: str
    entity_type: str
    entity_id: str
    related_entity_type: Optional[str]
    related_entity_id: Optional[str]
    message: str
    technical_explanation: str
    geometry_wkt: Optional[str]
    geometry_geojson: Optional[Dict[str, Any]] = None
    measured_value: Optional[str]
    expected_value: Optional[str]
    tolerance: Optional[str]
    metadata_json: Dict[str, Any]
    created_at: datetime
    acknowledged_at: Optional[datetime]
    acknowledged_by: Optional[uuid.UUID]
    resolved_at: Optional[datetime]
    resolved_by: Optional[uuid.UUID]
    resolution_note: Optional[str]
    waived_at: Optional[datetime]
    waived_by: Optional[uuid.UUID]
    waiver_reason: Optional[str]



class ValidationIssueActionRequest(BaseModel):
    """Human review decision on a validation issue."""
    action: str = Field(
        ...,
        description="Review action: ACKNOWLEDGE, RESOLVE, WAIVE",
    )
    note: Optional[str] = Field(
        None,
        description="Resolution note (mandatory when resolving).",
    )
    reason: Optional[str] = Field(
        None,
        description="Waiver justification (mandatory when waiving).",
    )


class ValidationRuleResponse(BaseModel):
    rule_id: str
    name: str
    description: str
    category: str
    severity: str
    rule_version: str


class EntityValidationSummaryResponse(BaseModel):
    entity_type: str
    entity_id: str
    latest_run_id: Optional[uuid.UUID]
    status: str
    total_issues: int
    critical_issues: int
    error_issues: int
    warning_issues: int
    info_issues: int
    open_issues: int
    resolved_issues: int
    waived_issues: int
    last_validated_at: Optional[datetime]

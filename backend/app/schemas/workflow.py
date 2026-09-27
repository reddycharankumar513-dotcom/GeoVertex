"""Pydantic V2 schemas for Citizen Portal & Government Workflows."""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


# 1. Service Types
class ServiceTypeCreate(BaseModel):
    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    citizen_visible: bool = True
    required_documents: List[str] = Field(default_factory=list)
    required_fields: List[str] = Field(default_factory=list)
    response_sla_hours: int = 24
    completion_sla_hours: int = 120
    allowed_roles: List[str] = Field(default_factory=lambda: ["CITIZEN", "GOVERNMENT_OFFICER", "ADMIN"])


class ServiceTypeResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: Optional[str] = None
    active: bool
    citizen_visible: bool
    required_documents: List[str] = Field(default_factory=list)
    required_fields: List[str] = Field(default_factory=list)
    response_sla_hours: int
    completion_sla_hours: int
    allowed_roles: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 2. Service Requests
class ServiceRequestCreate(BaseModel):
    request_type: str = Field(..., max_length=64)
    jurisdiction_id: uuid.UUID
    property_id: Optional[uuid.UUID] = None
    parcel_id: Optional[uuid.UUID] = None
    building_id: Optional[uuid.UUID] = None
    floor_id: Optional[uuid.UUID] = None
    unit_id: Optional[uuid.UUID] = None
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10)
    priority: str = Field("NORMAL", max_length=32)
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class ServiceRequestUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, min_length=10)
    priority: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None


class WorkflowTransitionPayload(BaseModel):
    target_status: str = Field(..., max_length=32)
    reason: Optional[str] = Field(None, max_length=255)
    comment: Optional[str] = None
    is_internal: bool = False


class CaseAssignmentPayload(BaseModel):
    assigned_to: Optional[uuid.UUID] = None
    assigned_team: Optional[str] = None
    reason: str = Field(..., min_length=3, max_length=255)


class SurveyCommissionPayload(BaseModel):
    surveyor_id: uuid.UUID
    instructions: str = Field(..., min_length=5)
    due_days: int = Field(7, ge=1, le=60)


class CaseEscalationPayload(BaseModel):
    escalate_to: uuid.UUID
    reason: str = Field(..., min_length=5)


class ControlledPropertyUpdatePayload(BaseModel):
    reason: str = Field(..., min_length=5)
    source_reference: str = Field(..., min_length=3)
    updates: Dict[str, Any]


class ServiceRequestResponse(BaseModel):
    id: uuid.UUID
    request_reference: str
    case_reference: str
    citizen_id: uuid.UUID
    jurisdiction_id: uuid.UUID
    property_id: Optional[uuid.UUID] = None
    parcel_id: Optional[uuid.UUID] = None
    building_id: Optional[uuid.UUID] = None
    floor_id: Optional[uuid.UUID] = None
    unit_id: Optional[uuid.UUID] = None
    request_type: str
    title: str
    description: str
    status: str
    priority: str
    assigned_to: Optional[uuid.UUID] = None
    assigned_team: Optional[str] = None
    survey_project_id: Optional[uuid.UUID] = None
    survey_assignment_id: Optional[uuid.UUID] = None
    assigned_surveyor_id: Optional[uuid.UUID] = None
    submitted_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    escalated_at: Optional[datetime] = None
    escalation_reason: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 3. Events & Timeline
class ServiceRequestEventResponse(BaseModel):
    id: uuid.UUID
    service_request_id: uuid.UUID
    previous_status: Optional[str] = None
    new_status: str
    actor_id: Optional[uuid.UUID] = None
    actor_role: str
    event_type: str
    reason: Optional[str] = None
    comment: Optional[str] = None
    is_internal: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 4. Messages
class CaseMessageCreate(BaseModel):
    content: str = Field(..., min_length=1)
    message_type: str = Field("PUBLIC_COMMENT", max_length=32)
    is_internal: bool = False
    attachment_ids: List[str] = Field(default_factory=list)


class CaseMessageResponse(BaseModel):
    id: uuid.UUID
    service_request_id: uuid.UUID
    sender_id: uuid.UUID
    sender_role: str
    message_type: str
    content: str
    attachment_ids: List[str] = Field(default_factory=list)
    is_internal: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 5. Workflow Tasks
class WorkflowTaskCreate(BaseModel):
    task_type: str = Field("GENERAL_REQUEST", max_length=64)
    assigned_to: Optional[uuid.UUID] = None
    assigned_team: Optional[str] = None
    priority: str = Field("NORMAL", max_length=32)
    due_at: Optional[datetime] = None


class WorkflowTaskUpdate(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None


class WorkflowTaskResponse(BaseModel):
    id: uuid.UUID
    service_request_id: uuid.UUID
    task_type: str
    assigned_to: Optional[uuid.UUID] = None
    assigned_team: Optional[str] = None
    status: str
    priority: str
    due_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 6. Notifications
class NotificationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    notification_type: str
    title: str
    message: str
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    delivery_channel: str
    read_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 7. Citizen Authorized Property View
class CitizenPropertyLinkCreate(BaseModel):
    citizen_id: uuid.UUID
    property_id: uuid.UUID
    authorization_type: str = "OWNER"
    status: str = "VERIFIED"


class CitizenPropertyLinkResponse(BaseModel):
    id: uuid.UUID
    citizen_id: uuid.UUID
    property_id: uuid.UUID
    authorization_type: str
    status: str
    verified_by: Optional[uuid.UUID] = None
    verified_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CitizenPropertyResponse(BaseModel):
    id: uuid.UUID
    property_id: Optional[uuid.UUID] = None
    property_reference: str
    parcel_id: uuid.UUID
    parcel_number: Optional[str] = None
    property_type: str
    status: str
    address: str
    locality: Optional[str] = None
    postal_code: Optional[str] = None
    description: Optional[str] = None
    authorization_type: str = "OWNER"
    link_status: str = "VERIFIED"
    units_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 8. Detailed Case View for Government / Citizen
class ServiceRequestDetailResponse(BaseModel):
    request: ServiceRequestResponse
    events: List[ServiceRequestEventResponse]
    messages: List[CaseMessageResponse]
    tasks: List[WorkflowTaskResponse]
    sla: Dict[str, Any]
    property_info: Optional[CitizenPropertyResponse] = None
    attached_documents: List[Dict[str, Any]] = Field(default_factory=list)
    linked_surveys: List[Dict[str, Any]] = Field(default_factory=list)
    validation_status: Optional[Dict[str, Any]] = None
    change_status: Optional[Dict[str, Any]] = None
    utility_status: Optional[Dict[str, Any]] = None


# 9. Dashboard Metrics Responses
class CitizenDashboardMetricsResponse(BaseModel):
    total_properties: int
    total_requests: int
    active_requests: int
    pending_citizen_action: int
    completed_requests: int
    unread_notifications: int


class GovernmentDashboardMetricsResponse(BaseModel):
    total_received: int
    pending_acknowledgement: int
    acknowledged: int
    in_progress: int
    awaiting_citizen: int
    completed: int
    overdue: int
    open_tasks: int

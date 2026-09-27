import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.jurisdiction import Jurisdiction
    from app.models.property import Property
    from app.models.parcel import Parcel
    from app.models.building import BuildingFootprint
    from app.models.survey import SurveyProject, SurveyAssignment


class RequestStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_FOR_CITIZEN = "WAITING_FOR_CITIZEN"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    RESUBMITTED = "RESUBMITTED"
    APPROVED = "APPROVED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class RequestPriority(str, enum.Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TaskType(str, enum.Enum):
    DOCUMENT_REVIEW = "DOCUMENT_REVIEW"
    SURVEY_REVIEW = "SURVEY_REVIEW"
    PROPERTY_CORRECTION = "PROPERTY_CORRECTION"
    TOPOLOGY_REVIEW = "TOPOLOGY_REVIEW"
    CHANGE_REVIEW = "CHANGE_REVIEW"
    UTILITY_REVIEW = "UTILITY_REVIEW"
    GENERAL_REQUEST = "GENERAL_REQUEST"


class TaskStatus(str, enum.Enum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class MessageType(str, enum.Enum):
    PUBLIC_COMMENT = "PUBLIC_COMMENT"
    INTERNAL_NOTE = "INTERNAL_NOTE"
    CLARIFICATION_REQUEST = "CLARIFICATION_REQUEST"
    CITIZEN_RESPONSE = "CITIZEN_RESPONSE"


class NotificationType(str, enum.Enum):
    REQUEST_SUBMITTED = "REQUEST_SUBMITTED"
    REQUEST_ACKNOWLEDGED = "REQUEST_ACKNOWLEDGED"
    ASSIGNMENT = "ASSIGNMENT"
    REVISION_REQUESTED = "REVISION_REQUESTED"
    DOCUMENT_REQUIRED = "DOCUMENT_REQUIRED"
    DOCUMENT_VERIFIED = "DOCUMENT_VERIFIED"
    SURVEY_SCHEDULED = "SURVEY_SCHEDULED"
    SURVEY_SUBMITTED = "SURVEY_SUBMITTED"
    REQUEST_APPROVED = "REQUEST_APPROVED"
    REQUEST_REJECTED = "REQUEST_REJECTED"
    REQUEST_COMPLETED = "REQUEST_COMPLETED"
    CASE_ESCALATED = "CASE_ESCALATED"


class DeliveryChannel(str, enum.Enum):
    IN_APP = "IN_APP"
    EMAIL_QUEUED = "EMAIL_QUEUED"
    EMAIL_NOT_CONFIGURED = "EMAIL_NOT_CONFIGURED"


class AuthorizationType(str, enum.Enum):
    OWNER = "OWNER"
    AUTHORIZED_REPRESENTATIVE = "AUTHORIZED_REPRESENTATIVE"
    OCCUPANT = "OCCUPANT"
    TENANT = "TENANT"


class LinkStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    VERIFIED = "VERIFIED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    REVOKED = "REVOKED"


class ServiceType(Base, TimestampMixin):
    """Configurable service request category and workflow SLA definition."""
    __tablename__ = "service_types"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    citizen_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    required_documents: Mapped[List[str]] = mapped_column(JSON, default=list)
    required_fields: Mapped[List[str]] = mapped_column(JSON, default=list)
    response_sla_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    completion_sla_hours: Mapped[int] = mapped_column(Integer, default=120, nullable=False)
    allowed_roles: Mapped[List[str]] = mapped_column(
        JSON,
        default=lambda: ["CITIZEN", "GOVERNMENT_OFFICER", "ADMIN"],
    )


class CitizenPropertyLink(Base, TimestampMixin):
    """Object-level authorization linking a citizen user to their verified property record."""
    __tablename__ = "citizen_property_links"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    citizen_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    authorization_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=AuthorizationType.OWNER.value,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=LinkStatus.VERIFIED.value,
        index=True,
    )
    verified_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    citizen: Mapped["User"] = relationship("User", foreign_keys=[citizen_id])
    property: Mapped["Property"] = relationship("Property")
    verifier: Mapped[Optional["User"]] = relationship("User", foreign_keys=[verified_by])

    __table_args__ = (
        UniqueConstraint("citizen_id", "property_id", name="uq_citizen_property"),
    )


class ServiceRequest(Base, TimestampMixin):
    """Core citizen service request and government case management record."""
    __tablename__ = "service_requests"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    request_reference: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        doc="Citizen-facing service reference e.g. GV-SR-2026-000123",
    )
    case_reference: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        doc="Internal government case identifier e.g. GV-CASE-2026-000123",
    )
    citizen_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("jurisdictions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("properties.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    parcel_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("parcels.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    building_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("buildings.id", ondelete="SET NULL"),
        nullable=True,
    )
    floor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("floors.id", ondelete="SET NULL"),
        nullable=True,
    )
    unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("property_units.id", ondelete="SET NULL"),
        nullable=True,
    )

    request_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=RequestStatus.DRAFT.value,
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=RequestPriority.NORMAL.value,
        index=True,
    )

    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assigned_team: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Phase 5 Surveyor Commissioning Integration
    survey_project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("survey_projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    survey_assignment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("survey_assignments.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_surveyor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    escalated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    escalation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    escalated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    escalated_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    # Relationships
    citizen: Mapped["User"] = relationship("User", foreign_keys=[citizen_id])
    jurisdiction: Mapped["Jurisdiction"] = relationship("Jurisdiction")
    property: Mapped[Optional["Property"]] = relationship("Property")
    parcel: Mapped[Optional["Parcel"]] = relationship("Parcel")
    building: Mapped[Optional["BuildingFootprint"]] = relationship("BuildingFootprint")
    officer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to])
    surveyor: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_surveyor_id])

    events: Mapped[List["ServiceRequestEvent"]] = relationship(
        "ServiceRequestEvent",
        back_populates="service_request",
        cascade="all, delete-orphan",
        order_by="ServiceRequestEvent.created_at",
    )
    tasks: Mapped[List["WorkflowTask"]] = relationship(
        "WorkflowTask",
        back_populates="service_request",
        cascade="all, delete-orphan",
    )
    messages: Mapped[List["CaseMessage"]] = relationship(
        "CaseMessage",
        back_populates="service_request",
        cascade="all, delete-orphan",
        order_by="CaseMessage.created_at",
    )


class ServiceRequestEvent(Base, TimestampMixin):
    """Immutable transition record for audit trails and case timeline."""
    __tablename__ = "service_request_events"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    service_request_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("service_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    previous_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    new_status: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_role: Mapped[str] = mapped_column(String(32), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, default="STATUS_CHANGE")
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_internal: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Internal officer notes/events hidden from citizens",
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    service_request: Mapped["ServiceRequest"] = relationship("ServiceRequest", back_populates="events")
    actor: Mapped[Optional["User"]] = relationship("User", foreign_keys=[actor_id])


class WorkflowTask(Base, TimestampMixin):
    """Operational work task assigned to government officers."""
    __tablename__ = "workflow_tasks"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    service_request_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("service_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=TaskType.GENERAL_REQUEST.value,
        index=True,
    )
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assigned_team: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=TaskStatus.OPEN.value,
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=RequestPriority.NORMAL.value,
    )
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    service_request: Mapped["ServiceRequest"] = relationship("ServiceRequest", back_populates="tasks")
    assignee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to])


class CaseMessage(Base, TimestampMixin):
    """Structured case communication thread between citizen and government officers."""
    __tablename__ = "case_messages"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    service_request_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("service_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_role: Mapped[str] = mapped_column(String(32), nullable=False)
    message_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=MessageType.PUBLIC_COMMENT.value,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_ids: Mapped[List[str]] = mapped_column(JSON, default=list)
    is_internal: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="If True, internal officer note hidden from citizens",
    )

    service_request: Mapped["ServiceRequest"] = relationship("ServiceRequest", back_populates="messages")
    sender: Mapped["User"] = relationship("User", foreign_keys=[sender_id])


class Notification(Base, TimestampMixin):
    """User notifications with multi-channel delivery abstraction."""
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notification_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=NotificationType.REQUEST_SUBMITTED.value,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    related_entity_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    related_entity_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    delivery_channel: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=DeliveryChannel.IN_APP.value,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="SENT",
    )
    severity: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="INFO",
    )
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, nullable=True)
    jurisdiction_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, nullable=True)
    workflow_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, nullable=True)
    case_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    recipient: Mapped["User"] = relationship("User", foreign_keys=[user_id])

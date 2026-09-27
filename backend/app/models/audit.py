import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID

if TYPE_CHECKING:
    from app.models.user import User


class AuditCategory(str, enum.Enum):
    AUTHENTICATION = "AUTHENTICATION"
    AUTHORIZATION = "AUTHORIZATION"
    PROPERTY = "PROPERTY"
    GIS = "GIS"
    SURVEY = "SURVEY"
    AI = "AI"
    VALIDATION = "VALIDATION"
    DOCUMENT = "DOCUMENT"
    CHANGE_DETECTION = "CHANGE_DETECTION"
    UTILITY = "UTILITY"
    IDENTIFIER = "IDENTIFIER"
    WORKFLOW = "WORKFLOW"
    NOTIFICATION = "NOTIFICATION"
    GOVERNANCE = "GOVERNANCE"
    ADMINISTRATION = "ADMINISTRATION"
    SYSTEM = "SYSTEM"


class AuditSeverity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AuditResult(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    DENIED = "DENIED"


class AuditEvent(Base):
    """Immutable audit trail recording security, operational, cadastral, and administrative actions."""
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    event_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Actor information
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_role: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        nullable=True,
    )
    jurisdiction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        nullable=True,
    )

    # Action & Category
    action: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=AuditCategory.SYSTEM.value,
    )
    severity: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=AuditSeverity.INFO.value,
    )
    result: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=AuditResult.SUCCESS.value,
    )

    # Entity context
    entity_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    entity_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    entity_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        nullable=True,
    )

    # Request & Workflow tracing
    request_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    correlation_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    workflow_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        nullable=True,
    )
    case_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )

    # Provenance
    source_type: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )
    source_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Safe snapshot diffs
    before_snapshot: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )
    after_snapshot: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )
    changed_fields: Mapped[List[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    geometry_changed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Client metadata
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
    )
    details: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )

    actor: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="audit_logs",
    )

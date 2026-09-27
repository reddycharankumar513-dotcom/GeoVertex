"""Phase 11: Citizen Portal, Government Workflow & Public-Service Integration

Revision ID: 011_phase11_citizen_workflow
Revises: 010_phase10_underground_infrastructure
Create Date: 2026-09-26 10:15:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa

revision: str = '011_phase11_citizen_workflow'
down_revision: Union[str, None] = '010_phase10_underground_infrastructure'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    # 1. Service Types Table
    op.create_table(
        'service_types',
        sa.Column('id', sa.CHAR(36) if not is_postgres else sa.UUID(), primary_key=True),
        sa.Column('code', sa.String(64), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), default=True, nullable=False),
        sa.Column('citizen_visible', sa.Boolean(), default=True, nullable=False),
        sa.Column('required_documents', sa.JSON(), nullable=False),
        sa.Column('required_fields', sa.JSON(), nullable=False),
        sa.Column('response_sla_hours', sa.Integer(), default=24, nullable=False),
        sa.Column('completion_sla_hours', sa.Integer(), default=120, nullable=False),
        sa.Column('allowed_roles', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_service_types_code', 'service_types', ['code'])

    # 2. Citizen Property Links Table
    op.create_table(
        'citizen_property_links',
        sa.Column('id', sa.CHAR(36) if not is_postgres else sa.UUID(), primary_key=True),
        sa.Column('citizen_id', sa.CHAR(36) if not is_postgres else sa.UUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('property_id', sa.CHAR(36) if not is_postgres else sa.UUID(), sa.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False),
        sa.Column('authorization_type', sa.String(32), default='OWNER', nullable=False),
        sa.Column('status', sa.String(32), default='VERIFIED', nullable=False),
        sa.Column('verified_by', sa.CHAR(36) if not is_postgres else sa.UUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('citizen_id', 'property_id', name='uq_citizen_property'),
    )
    op.create_index('ix_citizen_property_links_citizen_id', 'citizen_property_links', ['citizen_id'])
    op.create_index('ix_citizen_property_links_property_id', 'citizen_property_links', ['property_id'])
    op.create_index('ix_citizen_property_links_status', 'citizen_property_links', ['status'])

    # 3. Service Requests Table
    op.create_table(
        'service_requests',
        sa.Column('id', sa.CHAR(36) if not is_postgres else sa.UUID(), primary_key=True),
        sa.Column('request_reference', sa.String(64), unique=True, nullable=False),
        sa.Column('case_reference', sa.String(64), unique=True, nullable=False),
        sa.Column('citizen_id', sa.CHAR(36) if not is_postgres else sa.UUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('jurisdiction_id', sa.CHAR(36) if not is_postgres else sa.UUID(), sa.ForeignKey('jurisdictions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('property_id', sa.CHAR(36) if not is_postgres else sa.UUID(), sa.ForeignKey('properties.id', ondelete='SET NULL'), nullable=True),
        sa.Column('parcel_id', sa.CHAR(36) if not is_postgres else sa.UUID(), sa.ForeignKey('parcels.id', ondelete='SET NULL'), nullable=True),
        sa.Column('building_id', sa.CHAR(36) if not is_postgres else sa.UUID(), sa.ForeignKey('buildings.id', ondelete='SET NULL'), nullable=True),
        sa.Column('floor_id', sa.CHAR(36) if not is_postgres else sa.UUID(), sa.ForeignKey('floors.id', ondelete='SET NULL'), nullable=True),
        sa.Column('unit_id', sa.CHAR(36) if not is_postgres else sa.UUID(), sa.ForeignKey('property_units.id', ondelete='SET NULL'), nullable=True),
        sa.Column('request_type', sa.String(64), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.String(32), default='DRAFT', nullable=False),
        sa.Column('priority', sa.String(32), default='NORMAL', nullable=False),
        sa.Column('assigned_to', sa.CHAR(36) if not is_postgres else sa.UUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('assigned_team', sa.String(128), nullable=True),
        sa.Column('survey_project_id', sa.CHAR(36) if not is_postgres else sa.UUID(), sa.ForeignKey('survey_projects.id', ondelete='SET NULL'), nullable=True),
        sa.Column('survey_assignment_id', sa.CHAR(36) if not is_postgres else sa.UUID(), sa.ForeignKey('survey_assignments.id', ondelete='SET NULL'), nullable=True),
        sa.Column('assigned_surveyor_id', sa.CHAR(36) if not is_postgres else sa.UUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('escalated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('escalation_reason', sa.Text(), nullable=True),
        sa.Column('escalated_by', sa.CHAR(36) if not is_postgres else sa.UUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('escalated_to', sa.CHAR(36) if not is_postgres else sa.UUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_service_requests_request_reference', 'service_requests', ['request_reference'])
    op.create_index('ix_service_requests_case_reference', 'service_requests', ['case_reference'])
    op.create_index('ix_service_requests_citizen_id', 'service_requests', ['citizen_id'])
    op.create_index('ix_service_requests_jurisdiction_id', 'service_requests', ['jurisdiction_id'])
    op.create_index('ix_service_requests_property_id', 'service_requests', ['property_id'])
    op.create_index('ix_service_requests_parcel_id', 'service_requests', ['parcel_id'])
    op.create_index('ix_service_requests_request_type', 'service_requests', ['request_type'])
    op.create_index('ix_service_requests_status', 'service_requests', ['status'])
    op.create_index('ix_service_requests_priority', 'service_requests', ['priority'])
    op.create_index('ix_service_requests_assigned_to', 'service_requests', ['assigned_to'])
    op.create_index('ix_service_requests_due_at', 'service_requests', ['due_at'])

    # 4. Service Request Events (Timeline / Audit Trail)
    op.create_table(
        'service_request_events',
        sa.Column('id', sa.CHAR(36) if not is_postgres else sa.UUID(), primary_key=True),
        sa.Column('service_request_id', sa.CHAR(36) if not is_postgres else sa.UUID(), sa.ForeignKey('service_requests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('previous_status', sa.String(32), nullable=True),
        sa.Column('new_status', sa.String(32), nullable=False),
        sa.Column('actor_id', sa.CHAR(36) if not is_postgres else sa.UUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('actor_role', sa.String(32), nullable=False),
        sa.Column('event_type', sa.String(64), default='STATUS_CHANGE', nullable=False),
        sa.Column('reason', sa.String(255), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('is_internal', sa.Boolean(), default=False, nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_service_request_events_request_id', 'service_request_events', ['service_request_id'])

    # 5. Workflow Tasks (Government Work Queue)
    op.create_table(
        'workflow_tasks',
        sa.Column('id', sa.CHAR(36) if not is_postgres else sa.UUID(), primary_key=True),
        sa.Column('service_request_id', sa.CHAR(36) if not is_postgres else sa.UUID(), sa.ForeignKey('service_requests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('task_type', sa.String(64), nullable=False),
        sa.Column('assigned_to', sa.CHAR(36) if not is_postgres else sa.UUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('assigned_team', sa.String(128), nullable=True),
        sa.Column('status', sa.String(32), default='OPEN', nullable=False),
        sa.Column('priority', sa.String(32), default='NORMAL', nullable=False),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.CHAR(36) if not is_postgres else sa.UUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_workflow_tasks_request_id', 'workflow_tasks', ['service_request_id'])
    op.create_index('ix_workflow_tasks_assigned_to', 'workflow_tasks', ['assigned_to'])
    op.create_index('ix_workflow_tasks_status', 'workflow_tasks', ['status'])
    op.create_index('ix_workflow_tasks_task_type', 'workflow_tasks', ['task_type'])

    # 6. Case Messages (Citizen-Officer Thread)
    op.create_table(
        'case_messages',
        sa.Column('id', sa.CHAR(36) if not is_postgres else sa.UUID(), primary_key=True),
        sa.Column('service_request_id', sa.CHAR(36) if not is_postgres else sa.UUID(), sa.ForeignKey('service_requests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sender_id', sa.CHAR(36) if not is_postgres else sa.UUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sender_role', sa.String(32), nullable=False),
        sa.Column('message_type', sa.String(32), default='PUBLIC_COMMENT', nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('attachment_ids', sa.JSON(), nullable=False),
        sa.Column('is_internal', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_case_messages_request_id', 'case_messages', ['service_request_id'])
    op.create_index('ix_case_messages_sender_id', 'case_messages', ['sender_id'])

    # 7. Notifications Table
    op.create_table(
        'notifications',
        sa.Column('id', sa.CHAR(36) if not is_postgres else sa.UUID(), primary_key=True),
        sa.Column('user_id', sa.CHAR(36) if not is_postgres else sa.UUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('notification_type', sa.String(64), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('related_entity_type', sa.String(64), nullable=True),
        sa.Column('related_entity_id', sa.String(64), nullable=True),
        sa.Column('delivery_channel', sa.String(32), default='IN_APP', nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('ix_notifications_read_at', 'notifications', ['read_at'])


def downgrade() -> None:
    op.drop_table('notifications')
    op.drop_table('case_messages')
    op.drop_table('workflow_tasks')
    op.drop_table('service_request_events')
    op.drop_table('service_requests')
    op.drop_table('citizen_property_links')
    op.drop_table('service_types')

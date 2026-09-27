"""Phase 13 — Alembic migration for Audit, Versioning, Notifications and System Governance.

Revision ID: 013_phase13_governance
Revises: 012_phase12_identifier_engine
Create Date: 2026-09-27 10:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '013_phase13_governance'
down_revision: Union[str, None] = '012_phase12_identifier_engine'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'
    uuid_col = sa.UUID() if is_postgres else sa.CHAR(36)

    # ──────────────────────────────────────────────────
    # 1. Entity Versions
    # ──────────────────────────────────────────────────
    op.create_table(
        'entity_versions',
        sa.Column('id', uuid_col, primary_key=True),
        sa.Column('entity_type', sa.String(64), nullable=False),
        sa.Column('entity_id', sa.String(64), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('version_uuid', sa.String(64), unique=True, nullable=False),
        sa.Column('version_status', sa.String(32), nullable=False, server_default='CURRENT'),
        sa.Column('created_by', uuid_col, nullable=True),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('change_type', sa.String(32), nullable=False, server_default='UPDATE'),
        sa.Column('change_reason', sa.Text(), nullable=True),
        sa.Column('source_type', sa.String(32), nullable=False, server_default='SYSTEM'),
        sa.Column('source_id', sa.String(64), nullable=True),
        sa.Column('parent_version_id', uuid_col, nullable=True),
        sa.Column('supersedes_version_id', uuid_col, nullable=True),
        sa.Column('superseded_by_version_id', uuid_col, nullable=True),
        sa.Column('snapshot_data', sa.JSON(), nullable=False),
        sa.Column('geometry_wkt', sa.Text(), nullable=True),
        sa.Column('geometry_srid', sa.Integer(), nullable=True, server_default='4326'),
        sa.Column('geometry_type', sa.String(32), nullable=True),
        sa.Column('geometry_hash', sa.String(64), nullable=True),
        sa.Column('content_hash', sa.String(64), nullable=True),
        sa.Column('geometry_metrics', sa.JSON(), nullable=False),
        sa.Column('workflow_id', uuid_col, nullable=True),
        sa.Column('case_id', sa.String(64), nullable=True),
        sa.Column('correlation_id', sa.String(64), nullable=True),
        sa.Column('review_status', sa.String(32), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('entity_type', 'entity_id', 'version_number', name='uq_entity_version_number'),
    )

    # ──────────────────────────────────────────────────
    # 2. Entity Lineages
    # ──────────────────────────────────────────────────
    op.create_table(
        'entity_lineages',
        sa.Column('id', uuid_col, primary_key=True),
        sa.Column('source_entity_type', sa.String(64), nullable=False),
        sa.Column('source_entity_id', sa.String(64), nullable=False),
        sa.Column('source_version_id', uuid_col, nullable=True),
        sa.Column('target_entity_type', sa.String(64), nullable=False),
        sa.Column('target_entity_id', sa.String(64), nullable=False),
        sa.Column('target_version_id', uuid_col, nullable=True),
        sa.Column('relationship_type', sa.String(32), nullable=False, server_default='REPLACEMENT'),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('actor_user_id', uuid_col, nullable=True),
        sa.Column('workflow_id', uuid_col, nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # ──────────────────────────────────────────────────
    # 3. Notification Preferences
    # ──────────────────────────────────────────────────
    op.create_table(
        'notification_preferences',
        sa.Column('id', uuid_col, primary_key=True),
        sa.Column('user_id', uuid_col, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('notification_type', sa.String(64), nullable=False),
        sa.Column('channel', sa.String(32), nullable=False, server_default='IN_APP'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('digest_frequency', sa.String(32), nullable=False, server_default='IMMEDIATE'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('user_id', 'notification_type', 'channel', name='uq_user_notif_pref_channel'),
    )

    # ──────────────────────────────────────────────────
    # 4. Extend audit_logs
    # ──────────────────────────────────────────────────
    with op.batch_alter_table('audit_logs') as batch_op:
        batch_op.add_column(sa.Column('event_id', sa.String(64), nullable=True))
        batch_op.add_column(sa.Column('category', sa.String(32), nullable=True, server_default='SYSTEM'))
        batch_op.add_column(sa.Column('actor_role', sa.String(32), nullable=True))
        batch_op.add_column(sa.Column('organization_id', uuid_col, nullable=True))
        batch_op.add_column(sa.Column('jurisdiction_id', uuid_col, nullable=True))
        batch_op.add_column(sa.Column('entity_version_id', uuid_col, nullable=True))
        batch_op.add_column(sa.Column('request_id', sa.String(64), nullable=True))
        batch_op.add_column(sa.Column('correlation_id', sa.String(64), nullable=True))
        batch_op.add_column(sa.Column('workflow_id', uuid_col, nullable=True))
        batch_op.add_column(sa.Column('case_id', sa.String(64), nullable=True))
        batch_op.add_column(sa.Column('source_type', sa.String(32), nullable=True))
        batch_op.add_column(sa.Column('source_id', sa.String(64), nullable=True))
        batch_op.add_column(sa.Column('reason', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('before_snapshot', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('after_snapshot', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('changed_fields', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('geometry_changed', sa.Boolean(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('result', sa.String(32), nullable=True, server_default='SUCCESS'))
        batch_op.add_column(sa.Column('severity', sa.String(32), nullable=True, server_default='INFO'))

    # ──────────────────────────────────────────────────
    # 5. Extend notifications
    # ──────────────────────────────────────────────────
    with op.batch_alter_table('notifications') as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(32), nullable=True, server_default='SENT'))
        batch_op.add_column(sa.Column('severity', sa.String(32), nullable=True, server_default='INFO'))
        batch_op.add_column(sa.Column('organization_id', uuid_col, nullable=True))
        batch_op.add_column(sa.Column('jurisdiction_id', uuid_col, nullable=True))
        batch_op.add_column(sa.Column('workflow_id', uuid_col, nullable=True))
        batch_op.add_column(sa.Column('case_id', sa.String(64), nullable=True))
        batch_op.add_column(sa.Column('correlation_id', sa.String(64), nullable=True))
        batch_op.add_column(sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('retry_count', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('failure_reason', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('metadata_json', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_table('notification_preferences')
    op.drop_table('entity_lineages')
    op.drop_table('entity_versions')

"""Phase 7: Advanced Topology Validation & Spatial Consistency

Revision ID: 007_phase7_topology_validation
Revises: 006_phase6_ai_pipeline
Create Date: 2026-09-24 16:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

revision: str = '007_phase7_topology_validation'
down_revision: Union[str, None] = '006_phase6_ai_pipeline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    geom_col = (
        lambda: sa.Column('geometry', Geometry('GEOMETRY', srid=4326, spatial_index=False), nullable=True)
        if is_postgres
        else sa.Column('geometry', sa.Text(), nullable=True)
    )

    # 1. Validation Runs Table
    op.create_table(
        'validation_runs',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('validation_type', sa.String(64), nullable=False, server_default='SINGLE_ENTITY'),
        sa.Column('target_type', sa.String(64), nullable=False),
        sa.Column('target_id', sa.String(64), nullable=True),
        sa.Column('status', sa.String(32), nullable=False, server_default='QUEUED'),
        sa.Column('stage', sa.String(64), nullable=False, server_default='QUEUED'),
        sa.Column('requested_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('ruleset_version', sa.String(32), nullable=False, server_default='1.0.0'),
        sa.Column('parameters', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('summary', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_validation_runs_type', 'validation_runs', ['validation_type'])
    op.create_index('idx_validation_runs_target', 'validation_runs', ['target_type', 'target_id'])
    op.create_index('idx_validation_runs_status', 'validation_runs', ['status'])
    op.create_index('idx_validation_runs_requester', 'validation_runs', ['requested_by'])
    op.create_index('idx_validation_runs_created_at', 'validation_runs', ['created_at'])

    # 2. Validation Issues Table
    op.create_table(
        'validation_issues',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('validation_run_id', sa.CHAR(36), sa.ForeignKey('validation_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rule_id', sa.String(64), nullable=False),
        sa.Column('rule_version', sa.String(32), nullable=False, server_default='1.0.0'),
        sa.Column('issue_code', sa.String(64), nullable=False),
        sa.Column('category', sa.String(64), nullable=False),
        sa.Column('severity', sa.String(32), nullable=False),
        sa.Column('status', sa.String(32), nullable=False, server_default='OPEN'),
        sa.Column('entity_type', sa.String(64), nullable=False),
        sa.Column('entity_id', sa.String(64), nullable=False),
        sa.Column('related_entity_type', sa.String(64), nullable=True),
        sa.Column('related_entity_id', sa.String(64), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('technical_explanation', sa.Text(), nullable=False),
        geom_col(),
        sa.Column('geometry_wkt', sa.Text(), nullable=True),
        sa.Column('measured_value', sa.String(128), nullable=True),
        sa.Column('expected_value', sa.String(128), nullable=True),
        sa.Column('tolerance', sa.String(128), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('resolution_note', sa.Text(), nullable=True),
        sa.Column('waived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('waived_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('waiver_reason', sa.Text(), nullable=True),
    )
    op.create_index('idx_val_issues_run_id', 'validation_issues', ['validation_run_id'])
    op.create_index('idx_val_issues_rule_id', 'validation_issues', ['rule_id'])
    op.create_index('idx_val_issues_category', 'validation_issues', ['category'])
    op.create_index('idx_val_issues_severity', 'validation_issues', ['severity'])
    op.create_index('idx_val_issues_status', 'validation_issues', ['status'])
    op.create_index('idx_val_issues_entity', 'validation_issues', ['entity_type', 'entity_id'])
    op.create_index('idx_val_issues_related', 'validation_issues', ['related_entity_type', 'related_entity_id'])
    op.create_index('idx_val_issues_created_at', 'validation_issues', ['created_at'])

    if is_postgres:
        op.create_index('idx_val_issues_geom_gist', 'validation_issues', ['geometry'], postgresql_using='gist')


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    if is_postgres:
        op.drop_index('idx_val_issues_geom_gist', table_name='validation_issues')

    op.drop_index('idx_val_issues_created_at', table_name='validation_issues')
    op.drop_index('idx_val_issues_related', table_name='validation_issues')
    op.drop_index('idx_val_issues_entity', table_name='validation_issues')
    op.drop_index('idx_val_issues_status', table_name='validation_issues')
    op.drop_index('idx_val_issues_severity', table_name='validation_issues')
    op.drop_index('idx_val_issues_category', table_name='validation_issues')
    op.drop_index('idx_val_issues_rule_id', table_name='validation_issues')
    op.drop_index('idx_val_issues_run_id', table_name='validation_issues')
    op.drop_table('validation_issues')

    op.drop_index('idx_validation_runs_created_at', table_name='validation_runs')
    op.drop_index('idx_validation_runs_requester', table_name='validation_runs')
    op.drop_index('idx_validation_runs_status', table_name='validation_runs')
    op.drop_index('idx_validation_runs_target', table_name='validation_runs')
    op.drop_index('idx_validation_runs_type', table_name='validation_runs')
    op.drop_table('validation_runs')

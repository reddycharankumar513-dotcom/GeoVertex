"""Phase 5: Surveyor Field Workflow & Geospatial Data Collection

Revision ID: 005_phase5_survey_workflow
Revises: 004_phase4_floors_units
Create Date: 2026-09-23 21:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

revision: str = '005_phase5_survey_workflow'
down_revision: Union[str, None] = '004_phase4_floors_units'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    obs_geom_col = (
        sa.Column('geometry', Geometry('GEOMETRY', srid=4326, spatial_index=False), nullable=True)
        if is_postgres
        else sa.Column('geometry', sa.Text(), nullable=True)
    )

    # 1. Survey Projects Table
    op.create_table(
        'survey_projects',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('organization_id', sa.CHAR(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('jurisdiction_id', sa.CHAR(36), sa.ForeignKey('jurisdictions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('code', sa.String(64), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(32), nullable=False, server_default='DRAFT'),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_survey_projects_org_id', 'survey_projects', ['organization_id'])
    op.create_index('idx_survey_projects_jur_id', 'survey_projects', ['jurisdiction_id'])
    op.create_index('idx_survey_projects_code', 'survey_projects', ['code'])
    op.create_index('idx_survey_projects_status', 'survey_projects', ['status'])

    # 2. Survey Assignments Table
    op.create_table(
        'survey_assignments',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('survey_project_id', sa.CHAR(36), sa.ForeignKey('survey_projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('surveyor_id', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('jurisdiction_id', sa.CHAR(36), sa.ForeignKey('jurisdictions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('parcel_id', sa.CHAR(36), sa.ForeignKey('parcels.id', ondelete='SET NULL'), nullable=True),
        sa.Column('property_id', sa.CHAR(36), sa.ForeignKey('properties.id', ondelete='SET NULL'), nullable=True),
        sa.Column('building_id', sa.CHAR(36), sa.ForeignKey('buildings.id', ondelete='SET NULL'), nullable=True),
        sa.Column('floor_id', sa.CHAR(36), sa.ForeignKey('floors.id', ondelete='SET NULL'), nullable=True),
        sa.Column('unit_id', sa.CHAR(36), sa.ForeignKey('property_units.id', ondelete='SET NULL'), nullable=True),
        sa.Column('priority', sa.String(32), nullable=False, server_default='MEDIUM'),
        sa.Column('status', sa.String(32), nullable=False, server_default='ASSIGNED'),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_assignments_project_id', 'survey_assignments', ['survey_project_id'])
    op.create_index('idx_assignments_surveyor_id', 'survey_assignments', ['surveyor_id'])
    op.create_index('idx_assignments_jur_id', 'survey_assignments', ['jurisdiction_id'])
    op.create_index('idx_assignments_parcel_id', 'survey_assignments', ['parcel_id'])
    op.create_index('idx_assignments_building_id', 'survey_assignments', ['building_id'])
    op.create_index('idx_assignments_status', 'survey_assignments', ['status'])

    # 3. Survey Sessions Table
    op.create_table(
        'survey_sessions',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('assignment_id', sa.CHAR(36), sa.ForeignKey('survey_assignments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('surveyor_id', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(32), nullable=False, server_default='DRAFT'),
        sa.Column('device_identifier', sa.String(128), nullable=True),
        sa.Column('app_version', sa.String(32), nullable=True, server_default='1.0.0'),
        sa.Column('sync_status', sa.String(32), nullable=False, server_default='SYNCED'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_sessions_assignment_id', 'survey_sessions', ['assignment_id'])
    op.create_index('idx_sessions_surveyor_id', 'survey_sessions', ['surveyor_id'])
    op.create_index('idx_sessions_status', 'survey_sessions', ['status'])

    # 4. Survey Observations Table
    op.create_table(
        'survey_observations',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('session_id', sa.CHAR(36), sa.ForeignKey('survey_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('observation_type', sa.String(64), nullable=False),
        sa.Column('target_type', sa.String(32), nullable=False),
        sa.Column('target_id', sa.String(36), nullable=False),
        sa.Column('value', sa.String(255), nullable=False),
        sa.Column('unit', sa.String(32), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('captured_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('captured_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('horizontal_accuracy', sa.Float(), nullable=True),
        sa.Column('altitude', sa.Float(), nullable=True),
        sa.Column('vertical_accuracy', sa.Float(), nullable=True),
        sa.Column('source', sa.String(64), nullable=False, server_default='FIELD_OBSERVATION'),
        obs_geom_col,
        sa.Column('geometry_wkt', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_observations_session_id', 'survey_observations', ['session_id'])
    op.create_index('idx_observations_type', 'survey_observations', ['observation_type'])
    op.create_index('idx_observations_target', 'survey_observations', ['target_type', 'target_id'])
    op.create_index('idx_observations_captured_at', 'survey_observations', ['captured_at'])
    if is_postgres:
        op.create_index('idx_observations_geometry', 'survey_observations', ['geometry'], postgresql_using='gist')

    # 5. Survey Evidence Table
    op.create_table(
        'survey_evidence',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('session_id', sa.CHAR(36), sa.ForeignKey('survey_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('observation_id', sa.CHAR(36), sa.ForeignKey('survey_observations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('target_type', sa.String(32), nullable=False, server_default='BUILDING'),
        sa.Column('target_id', sa.String(36), nullable=False),
        sa.Column('storage_key', sa.String(512), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('mime_type', sa.String(128), nullable=False, server_default='image/jpeg'),
        sa.Column('file_size', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('evidence_type', sa.String(64), nullable=False, server_default='BUILDING_FRONT'),
        sa.Column('captured_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('accuracy', sa.Float(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sha256_hash', sa.String(64), nullable=False),
        sa.Column('uploaded_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_evidence_session_id', 'survey_evidence', ['session_id'])
    op.create_index('idx_evidence_observation_id', 'survey_evidence', ['observation_id'])
    op.create_index('idx_evidence_target', 'survey_evidence', ['target_type', 'target_id'])
    op.create_index('idx_evidence_hash', 'survey_evidence', ['sha256_hash'])

    # 6. Survey Submissions Table
    op.create_table(
        'survey_submissions',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('assignment_id', sa.CHAR(36), sa.ForeignKey('survey_assignments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('survey_session_id', sa.CHAR(36), sa.ForeignKey('survey_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(32), nullable=False, server_default='SUBMITTED'),
        sa.Column('snapshot_data', sa.Text(), nullable=False),
        sa.Column('submitted_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('reviewed_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('survey_session_id', 'version_number', name='uq_submissions_session_version'),
    )
    op.create_index('idx_submissions_assignment_id', 'survey_submissions', ['assignment_id'])
    op.create_index('idx_submissions_session_id', 'survey_submissions', ['survey_session_id'])
    op.create_index('idx_submissions_status', 'survey_submissions', ['status'])

    # 7. Sync Operations Table
    op.create_table(
        'sync_operations',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('client_operation_id', sa.String(128), nullable=False, unique=True),
        sa.Column('session_id', sa.CHAR(36), sa.ForeignKey('survey_sessions.id', ondelete='CASCADE'), nullable=True),
        sa.Column('operation_type', sa.String(64), nullable=False),
        sa.Column('entity_type', sa.String(64), nullable=False),
        sa.Column('entity_id', sa.String(64), nullable=False),
        sa.Column('payload', sa.Text(), nullable=False),
        sa.Column('status', sa.String(32), nullable=False, server_default='PENDING'),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_sync_client_op_id', 'sync_operations', ['client_operation_id'])
    op.create_index('idx_sync_session_id', 'sync_operations', ['session_id'])
    op.create_index('idx_sync_status', 'sync_operations', ['status'])


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    op.drop_index('idx_sync_status', table_name='sync_operations')
    op.drop_index('idx_sync_session_id', table_name='sync_operations')
    op.drop_index('idx_sync_client_op_id', table_name='sync_operations')
    op.drop_table('sync_operations')

    op.drop_index('idx_submissions_status', table_name='survey_submissions')
    op.drop_index('idx_submissions_session_id', table_name='survey_submissions')
    op.drop_index('idx_submissions_assignment_id', table_name='survey_submissions')
    op.drop_table('survey_submissions')

    op.drop_index('idx_evidence_hash', table_name='survey_evidence')
    op.drop_index('idx_evidence_target', table_name='survey_evidence')
    op.drop_index('idx_evidence_observation_id', table_name='survey_evidence')
    op.drop_index('idx_evidence_session_id', table_name='survey_evidence')
    op.drop_table('survey_evidence')

    if is_postgres:
        op.drop_index('idx_observations_geometry', table_name='survey_observations')
    op.drop_index('idx_observations_captured_at', table_name='survey_observations')
    op.drop_index('idx_observations_target', table_name='survey_observations')
    op.drop_index('idx_observations_type', table_name='survey_observations')
    op.drop_index('idx_observations_session_id', table_name='survey_observations')
    op.drop_table('survey_observations')

    op.drop_index('idx_sessions_status', table_name='survey_sessions')
    op.drop_index('idx_sessions_surveyor_id', table_name='survey_sessions')
    op.drop_index('idx_sessions_assignment_id', table_name='survey_sessions')
    op.drop_table('survey_sessions')

    op.drop_index('idx_assignments_status', table_name='survey_assignments')
    op.drop_index('idx_assignments_building_id', table_name='survey_assignments')
    op.drop_index('idx_assignments_parcel_id', table_name='survey_assignments')
    op.drop_index('idx_assignments_jur_id', table_name='survey_assignments')
    op.drop_index('idx_assignments_surveyor_id', table_name='survey_assignments')
    op.drop_index('idx_assignments_project_id', table_name='survey_assignments')
    op.drop_table('survey_assignments')

    op.drop_index('idx_survey_projects_status', table_name='survey_projects')
    op.drop_index('idx_survey_projects_code', table_name='survey_projects')
    op.drop_index('idx_survey_projects_jur_id', table_name='survey_projects')
    op.drop_index('idx_survey_projects_org_id', table_name='survey_projects')
    op.drop_table('survey_projects')

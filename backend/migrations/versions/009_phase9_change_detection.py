"""Phase 9: AI Change Detection & Temporal Property Intelligence

Revision ID: 009_phase9_change_detection
Revises: 008_phase8_document_intelligence
Create Date: 2026-09-24 21:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

revision: str = '009_phase9_change_detection'
down_revision: Union[str, None] = '008_phase8_document_intelligence'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    geom_col = (
        lambda name='geometry', nullable=True: sa.Column(name, Geometry('GEOMETRY', srid=4326, spatial_index=False), nullable=nullable)
        if is_postgres
        else sa.Column(name, sa.Text(), nullable=nullable)
    )

    # 1. Property Snapshots Table
    op.create_table(
        'property_snapshots',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('entity_type', sa.String(32), nullable=False),
        sa.Column('entity_id', sa.CHAR(36), nullable=False),
        sa.Column('snapshot_type', sa.String(32), nullable=False, server_default='OFFICIAL_RECORD'),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('observation_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('document_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('date_precision', sa.String(16), nullable=False, server_default='EXACT'),
        sa.Column('source_type', sa.String(64), nullable=False, server_default='OFFICIAL_RECORD'),
        sa.Column('source_id', sa.String(128), nullable=True),
        geom_col('geometry', nullable=True),
        sa.Column('geometry_wkt', sa.Text(), nullable=True),
        sa.Column('attributes_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('version_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default=sa.text('0' if not is_postgres else 'false')),
        sa.Column('created_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_snapshots_entity_type', 'property_snapshots', ['entity_type'])
    op.create_index('idx_snapshots_entity_id', 'property_snapshots', ['entity_id'])
    op.create_index('idx_snapshots_effective_from', 'property_snapshots', ['effective_from'])
    op.create_index('idx_snapshots_obs_date', 'property_snapshots', ['observation_date'])
    op.create_index('idx_snapshots_is_current', 'property_snapshots', ['is_current'])

    # 2. Change Detection Runs Table
    op.create_table(
        'change_detection_runs',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('target_type', sa.String(32), nullable=False),
        sa.Column('target_id', sa.CHAR(36), nullable=True),
        sa.Column('jurisdiction_id', sa.CHAR(36), nullable=True),
        sa.Column('baseline_reference', sa.String(128), nullable=False),
        sa.Column('comparison_reference', sa.String(128), nullable=False),
        sa.Column('detection_method', sa.String(32), nullable=False, server_default='GEOMETRY_DIFF'),
        sa.Column('status', sa.String(32), nullable=False, server_default='QUEUED'),
        sa.Column('requested_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('parameters', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ruleset_version', sa.String(32), nullable=False, server_default='1.0.0'),
        sa.Column('model_id', sa.String(64), nullable=True),
        sa.Column('model_version', sa.String(32), nullable=True),
        sa.Column('summary', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_change_runs_target_type', 'change_detection_runs', ['target_type'])
    op.create_index('idx_change_runs_target_id', 'change_detection_runs', ['target_id'])
    op.create_index('idx_change_runs_status', 'change_detection_runs', ['status'])
    op.create_index('idx_change_runs_method', 'change_detection_runs', ['detection_method'])

    # 3. Change Candidates Table
    op.create_table(
        'change_candidates',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('detection_run_id', sa.CHAR(36), sa.ForeignKey('change_detection_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('change_type', sa.String(64), nullable=False),
        sa.Column('entity_type', sa.String(32), nullable=False),
        sa.Column('entity_id', sa.CHAR(36), nullable=True),
        sa.Column('baseline_snapshot_id', sa.CHAR(36), sa.ForeignKey('property_snapshots.id', ondelete='SET NULL'), nullable=True),
        sa.Column('comparison_snapshot_id', sa.CHAR(36), sa.ForeignKey('property_snapshots.id', ondelete='SET NULL'), nullable=True),
        sa.Column('baseline_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('comparison_date', sa.DateTime(timezone=True), nullable=True),
        geom_col('geometry', nullable=True),
        sa.Column('geometry_wkt', sa.Text(), nullable=True),
        sa.Column('baseline_geometry_wkt', sa.Text(), nullable=True),
        sa.Column('comparison_geometry_wkt', sa.Text(), nullable=True),
        sa.Column('magnitude', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('significance', sa.String(32), nullable=False, server_default='MINOR'),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('evidence', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('validation_issues', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('status', sa.String(32), nullable=False, server_default='NEW'),
        sa.Column('review_reason', sa.String(64), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_change_cand_run', 'change_candidates', ['detection_run_id'])
    op.create_index('idx_change_cand_type', 'change_candidates', ['change_type'])
    op.create_index('idx_change_cand_entity', 'change_candidates', ['entity_type', 'entity_id'])
    op.create_index('idx_change_cand_status', 'change_candidates', ['status'])
    op.create_index('idx_change_cand_sig', 'change_candidates', ['significance'])

    # 4. Raster Observations Table
    op.create_table(
        'raster_observations',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('source', sa.String(32), nullable=False, server_default='ORTHOPHOTO'),
        sa.Column('acquisition_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('date_precision', sa.String(16), nullable=False, server_default='EXACT'),
        sa.Column('file_reference', sa.String(512), nullable=False),
        geom_col('footprint', nullable=True),
        sa.Column('footprint_wkt', sa.Text(), nullable=True),
        sa.Column('crs', sa.String(32), nullable=False, server_default='EPSG:4326'),
        sa.Column('resolution_meters', sa.Float(), nullable=True),
        sa.Column('checksum_sha256', sa.String(64), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_raster_obs_source', 'raster_observations', ['source'])
    op.create_index('idx_raster_obs_acq_date', 'raster_observations', ['acquisition_date'])


def downgrade() -> None:
    op.drop_table('raster_observations')
    op.drop_table('change_candidates')
    op.drop_table('change_detection_runs')
    op.drop_table('property_snapshots')

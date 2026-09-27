"""Phase 6: AI Building & Floor Extraction Pipeline

Revision ID: 006_phase6_ai_pipeline
Revises: 005_phase5_survey_workflow
Create Date: 2026-09-24 14:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

revision: str = '006_phase6_ai_pipeline'
down_revision: Union[str, None] = '005_phase5_survey_workflow'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    poly_geom_col = (
        lambda: sa.Column('geometry', Geometry('POLYGON', srid=4326, spatial_index=False), nullable=True)
        if is_postgres
        else sa.Column('geometry', sa.Text(), nullable=True)
    )

    # 1. AI Models Table
    op.create_table(
        'ai_models',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('model_id', sa.String(64), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('model_type', sa.String(64), nullable=False),
        sa.Column('framework', sa.String(64), nullable=False, server_default='PYTORCH'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(32), nullable=False, server_default='ACTIVE'),
        sa.Column('metadata_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_ai_models_model_id', 'ai_models', ['model_id'])
    op.create_index('idx_ai_models_type', 'ai_models', ['model_type'])
    op.create_index('idx_ai_models_status', 'ai_models', ['status'])

    # 2. AI Model Versions Table
    op.create_table(
        'ai_model_versions',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('model_id', sa.CHAR(36), sa.ForeignKey('ai_models.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version', sa.String(32), nullable=False),
        sa.Column('weights_reference', sa.String(512), nullable=True),
        sa.Column('weights_hash', sa.String(64), nullable=True),
        sa.Column('configuration', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('metrics', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1' if not is_postgres else 'true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('model_id', 'version', name='uq_model_versions_model_version'),
    )
    op.create_index('idx_ai_model_versions_model_id', 'ai_model_versions', ['model_id'])
    op.create_index('idx_ai_model_versions_version', 'ai_model_versions', ['version'])

    # 3. AI Processing Jobs Table
    op.create_table(
        'ai_processing_jobs',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('client_request_id', sa.String(128), nullable=True),
        sa.Column('job_type', sa.String(64), nullable=False),
        sa.Column('status', sa.String(32), nullable=False, server_default='QUEUED'),
        sa.Column('stage', sa.String(64), nullable=False, server_default='QUEUED'),
        sa.Column('progress_pct', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('requested_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('target_type', sa.String(32), nullable=False),
        sa.Column('target_id', sa.String(36), nullable=False),
        sa.Column('input_reference', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('model_id', sa.String(64), nullable=False, server_default='building-segmentation-v1'),
        sa.Column('model_version', sa.String(32), nullable=False, server_default='1.0.0'),
        sa.Column('parameters', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_code', sa.String(64), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_ai_jobs_status', 'ai_processing_jobs', ['status'])
    op.create_index('idx_ai_jobs_type', 'ai_processing_jobs', ['job_type'])
    op.create_index('idx_ai_jobs_target', 'ai_processing_jobs', ['target_type', 'target_id'])
    op.create_index('idx_ai_jobs_client_req', 'ai_processing_jobs', ['client_request_id'])
    op.create_index('idx_ai_jobs_created_at', 'ai_processing_jobs', ['created_at'])

    # 4. AI Reviews Table
    op.create_table(
        'ai_reviews',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('result_type', sa.String(32), nullable=False),
        sa.Column('result_id', sa.CHAR(36), nullable=False),
        sa.Column('reviewer_id', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('action', sa.String(32), nullable=False),
        sa.Column('original_geometry_wkt', sa.Text(), nullable=False),
        sa.Column('edited_geometry_wkt', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('applied_to_cadastre', sa.Boolean(), nullable=False, server_default=sa.text('0' if not is_postgres else 'false')),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_ai_reviews_result', 'ai_reviews', ['result_type', 'result_id'])
    op.create_index('idx_ai_reviews_reviewer', 'ai_reviews', ['reviewer_id'])
    op.create_index('idx_ai_reviews_action', 'ai_reviews', ['action'])

    # 5. Building Extraction Results Table
    op.create_table(
        'building_extraction_results',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('job_id', sa.CHAR(36), sa.ForeignKey('ai_processing_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_target_id', sa.String(36), nullable=False),
        poly_geom_col(),
        sa.Column('geometry_wkt', sa.Text(), nullable=False),
        sa.Column('raw_geometry_wkt', sa.Text(), nullable=True),
        sa.Column('estimated_height', sa.Float(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('confidence_components', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('cadastral_comparison', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('evidence_linkage', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('model_id', sa.String(64), nullable=False),
        sa.Column('model_version', sa.String(32), nullable=False),
        sa.Column('status', sa.String(32), nullable=False, server_default='CANDIDATE'),
        sa.Column('validation_status', sa.String(32), nullable=False, server_default='VALID'),
        sa.Column('validation_details', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('review_id', sa.CHAR(36), sa.ForeignKey('ai_reviews.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_building_results_job_id', 'building_extraction_results', ['job_id'])
    op.create_index('idx_building_results_target_id', 'building_extraction_results', ['source_target_id'])
    op.create_index('idx_building_results_status', 'building_extraction_results', ['status'])
    op.create_index('idx_building_results_model_version', 'building_extraction_results', ['model_id', 'model_version'])

    # 6. Floor Extraction Results Table
    op.create_table(
        'floor_extraction_results',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('job_id', sa.CHAR(36), sa.ForeignKey('ai_processing_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('building_id', sa.CHAR(36), sa.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('candidate_floor_number', sa.Integer(), nullable=False),
        sa.Column('floor_label', sa.String(128), nullable=False),
        sa.Column('base_elevation', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('top_elevation', sa.Float(), nullable=False, server_default='3.0'),
        sa.Column('height', sa.Float(), nullable=False, server_default='3.0'),
        poly_geom_col(),
        sa.Column('geometry_wkt', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('source', sa.String(64), nullable=False, server_default='AI_EXTRACTION'),
        sa.Column('status', sa.String(32), nullable=False, server_default='CANDIDATE'),
        sa.Column('validation_details', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('review_id', sa.CHAR(36), sa.ForeignKey('ai_reviews.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_floor_results_job_id', 'floor_extraction_results', ['job_id'])
    op.create_index('idx_floor_results_building_id', 'floor_extraction_results', ['building_id'])
    op.create_index('idx_floor_results_status', 'floor_extraction_results', ['status'])

    # 7. AI Datasets Table
    op.create_table(
        'ai_datasets',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('dataset_id', sa.String(64), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('version', sa.String(32), nullable=False, server_default='1.0.0'),
        sa.Column('dataset_type', sa.String(64), nullable=False, server_default='DEVELOPMENT_DATASET'),
        sa.Column('source', sa.String(255), nullable=False),
        sa.Column('sample_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('label_schema', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_ai_datasets_dataset_id', 'ai_datasets', ['dataset_id'])

    # 8. AI Evaluation Runs Table
    op.create_table(
        'ai_evaluation_runs',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('dataset_id', sa.CHAR(36), sa.ForeignKey('ai_datasets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('model_id', sa.String(64), nullable=False),
        sa.Column('model_version', sa.String(32), nullable=False),
        sa.Column('metrics', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('executed_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_ai_eval_dataset_id', 'ai_evaluation_runs', ['dataset_id'])
    op.create_index('idx_ai_eval_model', 'ai_evaluation_runs', ['model_id', 'model_version'])


def downgrade() -> None:
    op.drop_table('ai_evaluation_runs')
    op.drop_table('ai_datasets')
    op.drop_table('floor_extraction_results')
    op.drop_table('building_extraction_results')
    op.drop_table('ai_reviews')
    op.drop_table('ai_processing_jobs')
    op.drop_table('ai_model_versions')
    op.drop_table('ai_models')

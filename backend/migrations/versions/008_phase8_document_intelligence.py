"""Phase 8: AI Document Intelligence & Property Document Verification

Revision ID: 008_phase8_document_intelligence
Revises: 007_phase7_topology_validation
Create Date: 2026-09-24 20:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '008_phase8_document_intelligence'
down_revision: Union[str, None] = '007_phase7_topology_validation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Property Documents
    op.create_table(
        'property_documents',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('document_reference', sa.String(100), unique=True, nullable=False),
        sa.Column('document_type', sa.String(50), nullable=False, server_default='OTHER'),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='UPLOADED'),
        sa.Column('source_type', sa.String(50), nullable=False, server_default='MANUAL_UPLOAD'),
        sa.Column('uploaded_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('organization_id', sa.CHAR(36), sa.ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('jurisdiction_id', sa.CHAR(36), sa.ForeignKey('jurisdictions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('property_id', sa.CHAR(36), sa.ForeignKey('properties.id', ondelete='SET NULL'), nullable=True),
        sa.Column('parcel_id', sa.CHAR(36), sa.ForeignKey('parcels.id', ondelete='SET NULL'), nullable=True),
        sa.Column('building_id', sa.CHAR(36), sa.ForeignKey('buildings.id', ondelete='SET NULL'), nullable=True),
        sa.Column('floor_id', sa.CHAR(36), sa.ForeignKey('floors.id', ondelete='SET NULL'), nullable=True),
        sa.Column('unit_id', sa.CHAR(36), sa.ForeignKey('property_units.id', ondelete='SET NULL'), nullable=True),
        sa.Column('survey_id', sa.CHAR(36), nullable=True),
        sa.Column('current_version_id', sa.CHAR(36), nullable=True),
        sa.Column('page_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('language', sa.String(20), nullable=False, server_default='en'),
        sa.Column('document_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('issuing_authority', sa.String(255), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_doc_ref', 'property_documents', ['document_reference'])
    op.create_index('idx_doc_type', 'property_documents', ['document_type'])
    op.create_index('idx_doc_status', 'property_documents', ['status'])
    op.create_index('idx_doc_jurisdiction', 'property_documents', ['jurisdiction_id'])
    op.create_index('idx_doc_parcel', 'property_documents', ['parcel_id'])
    op.create_index('idx_doc_property', 'property_documents', ['property_id'])
    op.create_index('idx_doc_building', 'property_documents', ['building_id'])
    op.create_index('idx_doc_unit', 'property_documents', ['unit_id'])

    # 2. Document Versions
    op.create_table(
        'document_versions',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('document_id', sa.CHAR(36), sa.ForeignKey('property_documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('storage_key', sa.String(500), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('file_hash', sa.String(64), nullable=False),
        sa.Column('page_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('uploaded_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('processing_status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('source_notes', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_doc_version_doc', 'document_versions', ['document_id'])
    op.create_index('idx_doc_version_hash', 'document_versions', ['file_hash'])

    # 3. Document Pages
    op.create_table(
        'document_pages',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('document_version_id', sa.CHAR(36), sa.ForeignKey('document_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('image_reference', sa.String(500), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('rotation', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('processing_status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_doc_page_ver', 'document_pages', ['document_version_id', 'page_number'])

    # 4. Document OCR Results
    op.create_table(
        'document_ocr_results',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('document_version_id', sa.CHAR(36), sa.ForeignKey('document_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('page_id', sa.CHAR(36), sa.ForeignKey('document_pages.id', ondelete='CASCADE'), nullable=True),
        sa.Column('engine', sa.String(100), nullable=False),
        sa.Column('engine_version', sa.String(50), nullable=True),
        sa.Column('language', sa.String(20), nullable=False, server_default='en'),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('blocks_json', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_ocr_version', 'document_ocr_results', ['document_version_id'])
    op.create_index('idx_ocr_page', 'document_ocr_results', ['page_id'])

    # 5. Document Extracted Fields
    op.create_table(
        'document_extracted_fields',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('document_version_id', sa.CHAR(36), sa.ForeignKey('document_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('field_name', sa.String(100), nullable=False),
        sa.Column('field_value', sa.Text(), nullable=False),
        sa.Column('normalized_value', sa.Text(), nullable=True),
        sa.Column('data_type', sa.String(50), nullable=False, server_default='STRING'),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('bounding_box', sa.JSON(), nullable=True),
        sa.Column('extraction_method', sa.String(50), nullable=False, server_default='RULE_BASED'),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('confidence_level', sa.String(20), nullable=False, server_default='UNKNOWN'),
        sa.Column('evidence_text', sa.Text(), nullable=True),
        sa.Column('model_id', sa.String(100), nullable=True),
        sa.Column('model_version', sa.String(50), nullable=True),
        sa.Column('review_status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('reviewed_value', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_extracted_fields_ver', 'document_extracted_fields', ['document_version_id'])
    op.create_index('idx_extracted_fields_name', 'document_extracted_fields', ['field_name'])
    op.create_index('idx_extracted_fields_review', 'document_extracted_fields', ['review_status'])

    # 6. Document Processing Jobs
    op.create_table(
        'document_processing_jobs',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('document_version_id', sa.CHAR(36), sa.ForeignKey('document_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_type', sa.String(50), nullable=False, server_default='FULL_PIPELINE'),
        sa.Column('status', sa.String(50), nullable=False, server_default='QUEUED'),
        sa.Column('current_stage', sa.String(50), nullable=False, server_default='QUEUED'),
        sa.Column('requested_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('parameters', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('error_code', sa.String(100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_proc_job_ver', 'document_processing_jobs', ['document_version_id'])
    op.create_index('idx_proc_job_status', 'document_processing_jobs', ['status'])

    # 7. Document Entity Links
    op.create_table(
        'document_entity_links',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('document_id', sa.CHAR(36), sa.ForeignKey('property_documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.CHAR(36), nullable=False),
        sa.Column('link_method', sa.String(50), nullable=False, server_default='MANUAL'),
        sa.Column('match_score', sa.Float(), nullable=True),
        sa.Column('match_reason', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='CONFIRMED'),
        sa.Column('confirmed_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_doc_link_doc', 'document_entity_links', ['document_id'])
    op.create_index('idx_doc_link_entity', 'document_entity_links', ['entity_type', 'entity_id'])


def downgrade() -> None:
    op.drop_table('document_entity_links')
    op.drop_table('document_processing_jobs')
    op.drop_table('document_extracted_fields')
    op.drop_table('document_ocr_results')
    op.drop_table('document_pages')
    op.drop_table('document_versions')
    op.drop_table('property_documents')

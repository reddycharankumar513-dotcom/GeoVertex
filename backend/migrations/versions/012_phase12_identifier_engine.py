"""Phase 12 — Alembic migration for Technical 3D Property Identifier Engine.

Revision ID: 012_phase12_identifier_engine
Revises: 011_phase11_citizen_workflow
Create Date: 2026-09-26 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '012_phase12_identifier_engine'
down_revision: Union[str, None] = '011_phase11_citizen_workflow'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'
    uuid_col = sa.UUID() if is_postgres else sa.CHAR(36)

    # ──────────────────────────────────────────────────
    # 1. Identifier Schemes
    # ──────────────────────────────────────────────────
    op.create_table(
        'identifier_schemes',
        sa.Column('id', uuid_col, primary_key=True),
        sa.Column('scheme_code', sa.String(64), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('version', sa.Integer(), default=1, nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('prefix', sa.String(16), nullable=False, server_default='GV'),
        sa.Column('separator', sa.String(4), nullable=False, server_default='-'),
        sa.Column('jurisdiction_component', sa.String(128), nullable=False, server_default='strip_prefix_code'),
        sa.Column('parcel_component', sa.String(128), nullable=False, server_default='strip_prefix_code'),
        sa.Column('building_component', sa.String(128), nullable=False, server_default='strip_prefix_ref'),
        sa.Column('floor_component', sa.String(128), nullable=False, server_default='strip_floor_suffix'),
        sa.Column('unit_component', sa.String(128), nullable=False, server_default='strip_unit_suffix'),
        sa.Column('padding_rules', sa.JSON(), nullable=False),
        sa.Column('checksum_enabled', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_identifier_schemes_code', 'identifier_schemes', ['scheme_code'])
    op.create_index('ix_identifier_schemes_active', 'identifier_schemes', ['active'])

    # ──────────────────────────────────────────────────
    # 2. Property Identifiers
    # ──────────────────────────────────────────────────
    op.create_table(
        'property_identifiers',
        sa.Column('id', uuid_col, primary_key=True),
        sa.Column('identifier_value', sa.String(256), unique=True, nullable=False),
        sa.Column('identifier_type', sa.String(32), nullable=False, server_default='PROPERTY_3D_ID'),
        sa.Column('scheme_id', uuid_col, sa.ForeignKey('identifier_schemes.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('entity_type', sa.String(32), nullable=False),
        sa.Column('entity_id', sa.String(36), nullable=False),
        # Hierarchy context (string UUIDs, no FK for portability)
        sa.Column('jurisdiction_id', sa.String(36), nullable=True),
        sa.Column('parcel_id', sa.String(36), nullable=True),
        sa.Column('building_id', sa.String(36), nullable=True),
        sa.Column('floor_id', sa.String(36), nullable=True),
        sa.Column('unit_id', sa.String(36), nullable=True),
        # Component breakdown
        sa.Column('jurisdiction_component', sa.String(64), nullable=True),
        sa.Column('parcel_component', sa.String(64), nullable=True),
        sa.Column('building_component', sa.String(64), nullable=True),
        sa.Column('floor_component', sa.String(64), nullable=True),
        sa.Column('unit_component', sa.String(64), nullable=True),
        # Lifecycle
        sa.Column('status', sa.String(32), nullable=False, server_default='ACTIVE'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('issued_by', sa.String(36), nullable=True),
        # Supersession chain
        sa.Column('supersedes_identifier_id', sa.String(36), nullable=True),
        sa.Column('superseded_by_identifier_id', sa.String(36), nullable=True),
        # Verification
        sa.Column('verification_token', sa.String(256), nullable=True),
        # Metadata
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_property_identifiers_value', 'property_identifiers', ['identifier_value'])
    op.create_index('ix_property_identifiers_entity_type', 'property_identifiers', ['entity_type'])
    op.create_index('ix_property_identifiers_entity_id', 'property_identifiers', ['entity_id'])
    op.create_index('ix_property_identifiers_scheme_id', 'property_identifiers', ['scheme_id'])
    op.create_index('ix_property_identifiers_status', 'property_identifiers', ['status'])
    op.create_index('ix_property_identifiers_jurisdiction_id', 'property_identifiers', ['jurisdiction_id'])
    op.create_index('ix_property_identifiers_parcel_id', 'property_identifiers', ['parcel_id'])
    op.create_index('ix_property_identifiers_building_id', 'property_identifiers', ['building_id'])
    op.create_index('ix_property_identifiers_floor_id', 'property_identifiers', ['floor_id'])
    op.create_index('ix_property_identifiers_unit_id', 'property_identifiers', ['unit_id'])
    op.create_index('ix_property_identifiers_verification_token', 'property_identifiers', ['verification_token'])

    # ──────────────────────────────────────────────────
    # 3. Identifier Lineages
    # ──────────────────────────────────────────────────
    op.create_table(
        'identifier_lineages',
        sa.Column('id', uuid_col, primary_key=True),
        sa.Column('source_identifier_id', sa.String(36), nullable=False),
        sa.Column('target_identifier_id', sa.String(36), nullable=False),
        sa.Column('relationship_type', sa.String(32), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('effective_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_identifier_lineages_source', 'identifier_lineages', ['source_identifier_id'])
    op.create_index('ix_identifier_lineages_target', 'identifier_lineages', ['target_identifier_id'])

    # ──────────────────────────────────────────────────
    # 4. Identifier Generation Jobs
    # ──────────────────────────────────────────────────
    op.create_table(
        'identifier_generation_jobs',
        sa.Column('id', uuid_col, primary_key=True),
        sa.Column('scheme_id', uuid_col, sa.ForeignKey('identifier_schemes.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('scope', sa.JSON(), nullable=False),
        sa.Column('requested_by', sa.String(36), nullable=True),
        sa.Column('status', sa.String(32), nullable=False, server_default='QUEUED'),
        sa.Column('total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('eligible', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('generated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('blocked', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('conflicts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('skipped', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('result_summary', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_identifier_generation_jobs_status', 'identifier_generation_jobs', ['status'])
    op.create_index('ix_identifier_generation_jobs_scheme', 'identifier_generation_jobs', ['scheme_id'])


def downgrade() -> None:
    op.drop_table('identifier_generation_jobs')
    op.drop_table('identifier_lineages')
    op.drop_table('property_identifiers')
    op.drop_table('identifier_schemes')

"""Phase 3: 3D Digital Twin & Vertical Spatial Foundation

Revision ID: 003_phase3_3d_digital_twin
Revises: 002_phase2_cadastral_gis
Create Date: 2026-09-23 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_phase3_3d_digital_twin'
down_revision: Union[str, None] = '002_phase2_cadastral_gis'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Building 3D Representations Table
    op.create_table(
        'building_3d_representations',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column(
            'building_id',
            sa.CHAR(36),
            sa.ForeignKey('buildings.id', ondelete='CASCADE', name='fk_building_3d_building'),
            nullable=False,
            unique=True,
        ),
        sa.Column('geometry_type', sa.String(64), nullable=False, server_default='EXTRUSION'),
        sa.Column('height', sa.Float(), nullable=False, server_default='12.0'),
        sa.Column('height_source', sa.String(64), nullable=False, server_default='ESTIMATED'),
        sa.Column('height_confidence', sa.Float(), nullable=True),
        sa.Column('height_unit', sa.String(32), nullable=False, server_default='METERS'),
        sa.Column('base_elevation', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('elevation_source', sa.String(64), nullable=False, server_default='LOCAL_REFERENCE_PLANE'),
        sa.Column('vertical_reference', sa.String(64), nullable=False, server_default='METERS_ABOVE_GROUND'),
        sa.Column('model_source', sa.String(64), nullable=False, server_default='EXTRUDED_FOOTPRINT'),
        sa.Column('model_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(32), nullable=False, server_default='ACTIVE'),
        sa.Column(
            'created_by',
            sa.CHAR(36),
            sa.ForeignKey('users.id', ondelete='SET NULL', name='fk_building_3d_created_by'),
            nullable=True,
        ),
        sa.Column(
            'updated_by',
            sa.CHAR(36),
            sa.ForeignKey('users.id', ondelete='SET NULL', name='fk_building_3d_updated_by'),
            nullable=True,
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_bldg_3d_rep_bldg_id', 'building_3d_representations', ['building_id'])
    op.create_index('idx_bldg_3d_rep_status', 'building_3d_representations', ['status'])

    # 2. ThreeD Assets Table
    op.create_table(
        'threed_assets',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column(
            'building_id',
            sa.CHAR(36),
            sa.ForeignKey('buildings.id', ondelete='CASCADE', name='fk_threed_assets_building'),
            nullable=True,
        ),
        sa.Column(
            'representation_id',
            sa.CHAR(36),
            sa.ForeignKey('building_3d_representations.id', ondelete='CASCADE', name='fk_threed_assets_representation'),
            nullable=True,
        ),
        sa.Column('asset_type', sa.String(64), nullable=False, server_default='EXTRUSION'),
        sa.Column('storage_location', sa.String(512), nullable=False, server_default='virtual://extrusions'),
        sa.Column('format', sa.String(64), nullable=False, server_default='JSON_EXTRUSION'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(32), nullable=False, server_default='ACTIVE'),
        sa.Column('source', sa.String(64), nullable=False, server_default='SYSTEM_GENERATED'),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column(
            'created_by',
            sa.CHAR(36),
            sa.ForeignKey('users.id', ondelete='SET NULL', name='fk_threed_assets_created_by'),
            nullable=True,
        ),
        sa.Column(
            'updated_by',
            sa.CHAR(36),
            sa.ForeignKey('users.id', ondelete='SET NULL', name='fk_threed_assets_updated_by'),
            nullable=True,
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_threed_assets_building_id', 'threed_assets', ['building_id'])
    op.create_index('idx_threed_assets_rep_id', 'threed_assets', ['representation_id'])
    op.create_index('idx_threed_assets_type', 'threed_assets', ['asset_type'])


def downgrade() -> None:
    op.drop_index('idx_threed_assets_type', table_name='threed_assets')
    op.drop_index('idx_threed_assets_rep_id', table_name='threed_assets')
    op.drop_index('idx_threed_assets_building_id', table_name='threed_assets')
    op.drop_table('threed_assets')

    op.drop_index('idx_bldg_3d_rep_status', table_name='building_3d_representations')
    op.drop_index('idx_bldg_3d_rep_bldg_id', table_name='building_3d_representations')
    op.drop_table('building_3d_representations')

"""Phase 2: Cadastral GIS - Parcels, Properties, Buildings, Boundaries

Revision ID: 002_phase2_cadastral_gis
Revises: 001_initial_schema
Create Date: 2026-09-22 21:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

revision: str = '002_phase2_cadastral_gis'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    # 1. Extend Jurisdictions table
    with op.batch_alter_table('jurisdictions') as batch_op:
        batch_op.add_column(sa.Column('parent_jurisdiction_id', sa.CHAR(36), sa.ForeignKey('jurisdictions.id', ondelete='SET NULL', name='fk_jurisdictions_parent_jurisdiction'), nullable=True))
        batch_op.add_column(sa.Column('description', sa.Text(), nullable=True))
        batch_op.create_index('idx_jurisdictions_parent_id', ['parent_jurisdiction_id'])


    # 2. Parcels Table
    parcel_geom_col = (
        sa.Column('geometry', Geometry('GEOMETRY', srid=4326, spatial_index=False), nullable=False)
        if is_postgres
        else sa.Column('geometry', sa.Text(), nullable=False)
    )

    op.create_table(
        'parcels',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('jurisdiction_id', sa.CHAR(36), sa.ForeignKey('jurisdictions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('parcel_number', sa.String(64), nullable=False),
        sa.Column('parcel_code', sa.String(128), nullable=False, unique=True),
        sa.Column('survey_number', sa.String(64), nullable=True),
        sa.Column('subdivision_number', sa.String(64), nullable=True),
        sa.Column('land_use', sa.String(64), nullable=False, server_default='RESIDENTIAL'),
        sa.Column('area', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('area_unit', sa.String(32), nullable=False, server_default='SQ_METER'),
        sa.Column('status', sa.String(64), nullable=False, server_default='ACTIVE'),
        sa.Column('ownership_status', sa.String(64), nullable=False, server_default='RECORDED'),
        parcel_geom_col,
        sa.Column('geometry_wkt', sa.Text(), nullable=True),
        sa.Column('centroid_lon', sa.Float(), nullable=True),
        sa.Column('centroid_lat', sa.Float(), nullable=True),
        sa.Column('source', sa.String(64), nullable=False, server_default='MANUAL'),
        sa.Column('source_reference', sa.String(255), nullable=True),
        sa.Column('source_file', sa.String(255), nullable=True),
        sa.Column('source_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('updated_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('jurisdiction_id', 'parcel_number', name='uq_parcels_jurisdiction_parcel_number'),
    )
    op.create_index('idx_parcels_jurisdiction_id', 'parcels', ['jurisdiction_id'])
    op.create_index('idx_parcels_number', 'parcels', ['parcel_number'])
    op.create_index('idx_parcels_code', 'parcels', ['parcel_code'])
    op.create_index('idx_parcels_survey', 'parcels', ['survey_number'])
    op.create_index('idx_parcels_land_use', 'parcels', ['land_use'])
    op.create_index('idx_parcels_status', 'parcels', ['status'])

    if is_postgres:
        op.execute("CREATE INDEX idx_parcels_geometry ON parcels USING GIST (geometry);")

    # 3. Properties Table
    op.create_table(
        'properties',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('parcel_id', sa.CHAR(36), sa.ForeignKey('parcels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('property_reference', sa.String(128), nullable=False, unique=True),
        sa.Column('property_type', sa.String(64), nullable=False, server_default='FREEHOLD'),
        sa.Column('status', sa.String(64), nullable=False, server_default='ACTIVE'),
        sa.Column('address', sa.String(512), nullable=False),
        sa.Column('locality', sa.String(255), nullable=True),
        sa.Column('postal_code', sa.String(32), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('updated_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_properties_parcel_id', 'properties', ['parcel_id'])
    op.create_index('idx_properties_reference', 'properties', ['property_reference'])
    op.create_index('idx_properties_status', 'properties', ['status'])

    # 4. Building Footprints Table
    building_geom_col = (
        sa.Column('geometry', Geometry('GEOMETRY', srid=4326, spatial_index=False), nullable=False)
        if is_postgres
        else sa.Column('geometry', sa.Text(), nullable=False)
    )

    op.create_table(
        'buildings',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('parcel_id', sa.CHAR(36), sa.ForeignKey('parcels.id', ondelete='CASCADE'), nullable=True),
        sa.Column('building_reference', sa.String(128), nullable=False, unique=True),
        sa.Column('building_type', sa.String(64), nullable=False, server_default='RESIDENTIAL'),
        sa.Column('status', sa.String(64), nullable=False, server_default='EXISTING'),
        sa.Column('area', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('height_estimate', sa.Float(), nullable=True),
        building_geom_col,
        sa.Column('geometry_wkt', sa.Text(), nullable=True),
        sa.Column('source', sa.String(64), nullable=False, server_default='SURVEY'),
        sa.Column('source_reference', sa.String(255), nullable=True),
        sa.Column('created_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('updated_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_buildings_parcel_id', 'buildings', ['parcel_id'])
    op.create_index('idx_buildings_reference', 'buildings', ['building_reference'])
    op.create_index('idx_buildings_status', 'buildings', ['status'])

    if is_postgres:
        op.execute("CREATE INDEX idx_buildings_geometry ON buildings USING GIST (geometry);")


def downgrade() -> None:
    op.drop_table('buildings')
    op.drop_table('properties')
    op.drop_table('parcels')
    with op.batch_alter_table('jurisdictions') as batch_op:
        batch_op.drop_index('idx_jurisdictions_parent_id')
        batch_op.drop_column('description')
        batch_op.drop_column('parent_jurisdiction_id')


"""Phase 4: Building, Floor & Unit Hierarchy

Revision ID: 004_phase4_floors_units
Revises: 003_phase3_3d_digital_twin
Create Date: 2026-09-23 10:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

revision: str = '004_phase4_floors_units'
down_revision: Union[str, None] = '003_phase3_3d_digital_twin'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    # Safe Geometry column definitions
    floor_geom_col = (
        sa.Column('geometry', Geometry('GEOMETRY', srid=4326, spatial_index=False), nullable=False)
        if is_postgres
        else sa.Column('geometry', sa.Text(), nullable=False)
    )
    unit_geom_col = (
        sa.Column('geometry', Geometry('GEOMETRY', srid=4326, spatial_index=False), nullable=False)
        if is_postgres
        else sa.Column('geometry', sa.Text(), nullable=False)
    )

    # 1. Floors Table
    op.create_table(
        'floors',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('building_id', sa.CHAR(36), sa.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('floor_number', sa.Integer(), nullable=False),
        sa.Column('floor_code', sa.String(128), nullable=False, unique=True),
        sa.Column('floor_name', sa.String(128), nullable=True),
        sa.Column('floor_type', sa.String(64), nullable=False, server_default='RESIDENTIAL'),
        sa.Column('elevation_min_m', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('elevation_max_m', sa.Float(), nullable=False, server_default='3.0'),
        sa.Column('height_m', sa.Float(), nullable=False, server_default='3.0'),
        sa.Column('area_sqm', sa.Float(), nullable=False, server_default='0.0'),
        floor_geom_col,
        sa.Column('geometry_wkt', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('status', sa.String(32), nullable=False, server_default='ACTIVE'),
        sa.Column('source', sa.String(64), nullable=False, server_default='SURVEY'),
        sa.Column('created_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('updated_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('building_id', 'floor_number', name='uq_floors_building_floor_number'),
    )
    op.create_index('idx_floors_building_id', 'floors', ['building_id'])
    op.create_index('idx_floors_floor_code', 'floors', ['floor_code'])
    op.create_index('idx_floors_status', 'floors', ['status'])
    if is_postgres:
        op.create_index('idx_floors_geometry', 'floors', ['geometry'], postgresql_using='gist')

    # 2. Property Units Table
    op.create_table(
        'property_units',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('floor_id', sa.CHAR(36), sa.ForeignKey('floors.id', ondelete='CASCADE'), nullable=False),
        sa.Column('building_id', sa.CHAR(36), sa.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('property_id', sa.CHAR(36), sa.ForeignKey('properties.id', ondelete='SET NULL'), nullable=True),
        sa.Column('unit_number', sa.String(64), nullable=False),
        sa.Column('unit_code', sa.String(128), nullable=False, unique=True),
        sa.Column('unit_type', sa.String(64), nullable=False, server_default='APARTMENT'),
        sa.Column('gross_area_sqm', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('net_area_sqm', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('elevation_min_m', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('elevation_max_m', sa.Float(), nullable=False, server_default='3.0'),
        sa.Column('height_m', sa.Float(), nullable=False, server_default='3.0'),
        unit_geom_col,
        sa.Column('geometry_wkt', sa.Text(), nullable=True),
        sa.Column('status', sa.String(32), nullable=False, server_default='ACTIVE'),
        sa.Column('ownership_status', sa.String(64), nullable=False, server_default='PRIVATE'),
        sa.Column('created_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('updated_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('floor_id', 'unit_number', name='uq_units_floor_unit_number'),
    )
    op.create_index('idx_units_floor_id', 'property_units', ['floor_id'])
    op.create_index('idx_units_building_id', 'property_units', ['building_id'])
    op.create_index('idx_units_property_id', 'property_units', ['property_id'])
    op.create_index('idx_units_unit_code', 'property_units', ['unit_code'])
    op.create_index('idx_units_status', 'property_units', ['status'])
    if is_postgres:
        op.create_index('idx_units_geometry', 'property_units', ['geometry'], postgresql_using='gist')


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    if is_postgres:
        op.drop_index('idx_units_geometry', table_name='property_units')
    op.drop_index('idx_units_status', table_name='property_units')
    op.drop_index('idx_units_unit_code', table_name='property_units')
    op.drop_index('idx_units_property_id', table_name='property_units')
    op.drop_index('idx_units_building_id', table_name='property_units')
    op.drop_index('idx_units_floor_id', table_name='property_units')
    op.drop_table('property_units')

    if is_postgres:
        op.drop_index('idx_floors_geometry', table_name='floors')
    op.drop_index('idx_floors_status', table_name='floors')
    op.drop_index('idx_floors_floor_code', table_name='floors')
    op.drop_index('idx_floors_building_id', table_name='floors')
    op.drop_table('floors')

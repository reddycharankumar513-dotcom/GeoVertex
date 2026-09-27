"""Phase 10: Underground Infrastructure & Subsurface Utility Intelligence

Revision ID: 010_phase10_underground_infrastructure
Revises: 009_phase9_change_detection
Create Date: 2026-09-24 21:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

revision: str = '010_phase10_underground_infrastructure'
down_revision: Union[str, None] = '009_phase9_change_detection'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    geom_col = (
        lambda geom_type='GEOMETRY', name='geometry', nullable=True: sa.Column(name, Geometry(geom_type, srid=4326, spatial_index=False), nullable=nullable)
        if is_postgres
        else sa.Column(name, sa.Text(), nullable=nullable)
    )

    # 1. Utility Networks Table
    op.create_table(
        'utility_networks',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('utility_type', sa.String(64), nullable=False, server_default='WATER'),
        sa.Column('owner_organization', sa.String(255), nullable=True),
        sa.Column('operator_organization', sa.String(255), nullable=True),
        sa.Column('jurisdiction_id', sa.CHAR(36), sa.ForeignKey('jurisdictions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(32), nullable=False, server_default='ACTIVE'),
        sa.Column('source', sa.String(64), nullable=False, server_default='OFFICIAL_RECORD'),
        sa.Column('metadata_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_utility_networks_name', 'utility_networks', ['name'])
    op.create_index('idx_utility_networks_type', 'utility_networks', ['utility_type'])
    op.create_index('idx_utility_networks_jurisdiction', 'utility_networks', ['jurisdiction_id'])
    op.create_index('idx_utility_networks_status', 'utility_networks', ['status'])

    # 2. Utility Assets Table
    op.create_table(
        'utility_assets',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('network_id', sa.CHAR(36), sa.ForeignKey('utility_networks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('asset_type', sa.String(64), nullable=False, server_default='PIPE'),
        sa.Column('asset_reference', sa.String(128), nullable=False),
        sa.Column('status', sa.String(32), nullable=False, server_default='ACTIVE'),
        sa.Column('review_status', sa.String(32), nullable=False, server_default='CANDIDATE'),
        geom_col('GEOMETRY', 'geometry', nullable=True),
        sa.Column('geometry_wkt', sa.Text(), nullable=True),
        sa.Column('geometry_type', sa.String(32), nullable=False, server_default='LINESTRING'),
        sa.Column('elevation_reference', sa.String(32), nullable=False, server_default='GROUND_RELATIVE'),
        sa.Column('depth', sa.Float(), nullable=True),
        sa.Column('depth_min', sa.Float(), nullable=True),
        sa.Column('depth_max', sa.Float(), nullable=True),
        sa.Column('ground_elevation', sa.Float(), nullable=True),
        sa.Column('centerline_elevation', sa.Float(), nullable=True),
        sa.Column('material', sa.String(128), nullable=True),
        sa.Column('diameter', sa.Float(), nullable=True),
        sa.Column('width', sa.Float(), nullable=True),
        sa.Column('capacity', sa.String(64), nullable=True),
        sa.Column('installation_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('commissioning_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source_type', sa.String(64), nullable=False, server_default='OFFICIAL_RECORD'),
        sa.Column('source_reference', sa.String(255), nullable=True),
        sa.Column('confidence', sa.String(32), nullable=False, server_default='MEDIUM'),
        sa.Column('parcel_id', sa.CHAR(36), sa.ForeignKey('parcels.id', ondelete='SET NULL'), nullable=True),
        sa.Column('building_id', sa.CHAR(36), sa.ForeignKey('buildings.id', ondelete='SET NULL'), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_utility_assets_network', 'utility_assets', ['network_id'])
    op.create_index('idx_utility_assets_type', 'utility_assets', ['asset_type'])
    op.create_index('idx_utility_assets_ref', 'utility_assets', ['asset_reference'])
    op.create_index('idx_utility_assets_status', 'utility_assets', ['status'])
    op.create_index('idx_utility_assets_review', 'utility_assets', ['review_status'])
    op.create_index('idx_utility_assets_parcel', 'utility_assets', ['parcel_id'])
    op.create_index('idx_utility_assets_building', 'utility_assets', ['building_id'])
    op.create_index('idx_utility_assets_depth', 'utility_assets', ['depth'])

    # 3. Utility Nodes Table (created before segments so foreign keys resolve)
    op.create_table(
        'utility_nodes',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('network_id', sa.CHAR(36), sa.ForeignKey('utility_networks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('node_type', sa.String(64), nullable=False, server_default='JUNCTION'),
        sa.Column('asset_reference', sa.String(128), nullable=False),
        geom_col('POINT', 'geometry', nullable=True),
        sa.Column('geometry_wkt', sa.Text(), nullable=True),
        sa.Column('elevation', sa.Float(), nullable=True),
        sa.Column('depth', sa.Float(), nullable=True),
        sa.Column('status', sa.String(32), nullable=False, server_default='ACTIVE'),
        sa.Column('source', sa.String(64), nullable=False, server_default='OFFICIAL_RECORD'),
        sa.Column('metadata_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_utility_nodes_network', 'utility_nodes', ['network_id'])
    op.create_index('idx_utility_nodes_type', 'utility_nodes', ['node_type'])
    op.create_index('idx_utility_nodes_ref', 'utility_nodes', ['asset_reference'])

    # 4. Utility Segments Table
    op.create_table(
        'utility_segments',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('utility_asset_id', sa.CHAR(36), sa.ForeignKey('utility_assets.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('start_node_id', sa.CHAR(36), sa.ForeignKey('utility_nodes.id', ondelete='SET NULL'), nullable=True),
        sa.Column('end_node_id', sa.CHAR(36), sa.ForeignKey('utility_nodes.id', ondelete='SET NULL'), nullable=True),
        geom_col('LINESTRING', 'geometry', nullable=True),
        sa.Column('geometry_wkt', sa.Text(), nullable=True),
        sa.Column('length_meters', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('depth_start', sa.Float(), nullable=True),
        sa.Column('depth_end', sa.Float(), nullable=True),
        sa.Column('elevation_start', sa.Float(), nullable=True),
        sa.Column('elevation_end', sa.Float(), nullable=True),
        sa.Column('slope_percentage', sa.Float(), nullable=True),
        sa.Column('flow_direction', sa.String(32), nullable=False, server_default='UNKNOWN'),
        sa.Column('status', sa.String(32), nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_utility_segments_asset', 'utility_segments', ['utility_asset_id'])
    op.create_index('idx_utility_segments_start', 'utility_segments', ['start_node_id'])
    op.create_index('idx_utility_segments_end', 'utility_segments', ['end_node_id'])

    # 5. Utility Structures Table
    op.create_table(
        'utility_structures',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('utility_asset_id', sa.CHAR(36), sa.ForeignKey('utility_assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('structure_type', sa.String(64), nullable=False, server_default='VAULT'),
        geom_col('GEOMETRY', 'geometry', nullable=True),
        sa.Column('geometry_wkt', sa.Text(), nullable=True),
        sa.Column('top_elevation', sa.Float(), nullable=True),
        sa.Column('bottom_elevation', sa.Float(), nullable=True),
        sa.Column('depth', sa.Float(), nullable=True),
        sa.Column('width_m', sa.Float(), nullable=True),
        sa.Column('length_m', sa.Float(), nullable=True),
        sa.Column('height_m', sa.Float(), nullable=True),
        sa.Column('source', sa.String(64), nullable=False, server_default='OFFICIAL_RECORD'),
        sa.Column('metadata_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_utility_structures_asset', 'utility_structures', ['utility_asset_id'])
    op.create_index('idx_utility_structures_type', 'utility_structures', ['structure_type'])

    # 6. Utility Corridors Table
    op.create_table(
        'utility_corridors',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('corridor_reference', sa.String(128), unique=True, nullable=False),
        sa.Column('jurisdiction_id', sa.CHAR(36), sa.ForeignKey('jurisdictions.id', ondelete='CASCADE'), nullable=False),
        geom_col('GEOMETRY', 'geometry', nullable=True),
        sa.Column('geometry_wkt', sa.Text(), nullable=True),
        sa.Column('width_meters', sa.Float(), nullable=False, server_default='5.0'),
        sa.Column('depth_range_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('utility_types', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('source', sa.String(64), nullable=False, server_default='OFFICIAL_RECORD'),
        sa.Column('status', sa.String(32), nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_utility_corridors_ref', 'utility_corridors', ['corridor_reference'])
    op.create_index('idx_utility_corridors_jurisdiction', 'utility_corridors', ['jurisdiction_id'])

    # 7. Utility Separation Rules Table
    op.create_table(
        'utility_separation_rules',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('rule_code', sa.String(64), unique=True, nullable=False),
        sa.Column('utility_type_a', sa.String(64), nullable=False),
        sa.Column('utility_type_b', sa.String(64), nullable=False),
        sa.Column('required_horizontal_separation_m', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('required_vertical_separation_m', sa.Float(), nullable=False, server_default='0.3'),
        sa.Column('jurisdiction_id', sa.CHAR(36), sa.ForeignKey('jurisdictions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('source', sa.String(128), nullable=False, server_default='MUNICIPAL_STANDARD'),
        sa.Column('version', sa.String(32), nullable=False, server_default='1.0'),
        sa.Column('effective_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(32), nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_separation_rules_code', 'utility_separation_rules', ['rule_code'])
    op.create_index('idx_separation_rules_types', 'utility_separation_rules', ['utility_type_a', 'utility_type_b'])

    # 8. Utility Clashes Table
    op.create_table(
        'utility_clashes',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('asset_a_id', sa.CHAR(36), sa.ForeignKey('utility_assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('asset_b_id', sa.CHAR(36), sa.ForeignKey('utility_assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('horizontal_relationship', sa.String(64), nullable=False, server_default='CROSSING'),
        sa.Column('vertical_relationship', sa.String(64), nullable=False, server_default='INSUFFICIENT_CLEARANCE'),
        sa.Column('measured_horizontal_separation_m', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('measured_vertical_separation_m', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('required_horizontal_separation_m', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('required_vertical_separation_m', sa.Float(), nullable=False, server_default='0.3'),
        sa.Column('clash_geometry_wkt', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(32), nullable=False, server_default='ERROR'),
        sa.Column('status', sa.String(32), nullable=False, server_default='OPEN'),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('resolved_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_clashes_asset_a', 'utility_clashes', ['asset_a_id'])
    op.create_index('idx_clashes_asset_b', 'utility_clashes', ['asset_b_id'])
    op.create_index('idx_clashes_status', 'utility_clashes', ['status'])
    op.create_index('idx_clashes_severity', 'utility_clashes', ['severity'])

    # 9. Utility Inspections Table
    op.create_table(
        'utility_inspections',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('utility_asset_id', sa.CHAR(36), sa.ForeignKey('utility_assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('inspection_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('inspector_id', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('condition', sa.String(64), nullable=False, server_default='GOOD'),
        sa.Column('depth_measurement', sa.Float(), nullable=True),
        sa.Column('observations', sa.Text(), nullable=True),
        sa.Column('evidence_references', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('status', sa.String(32), nullable=False, server_default='PASS'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_inspections_asset', 'utility_inspections', ['utility_asset_id'])
    op.create_index('idx_inspections_date', 'utility_inspections', ['inspection_date'])

    # 10. Utility Maintenance Events Table
    op.create_table(
        'utility_maintenance_events',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('utility_asset_id', sa.CHAR(36), sa.ForeignKey('utility_assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', sa.String(64), nullable=False, server_default='INSPECTION'),
        sa.Column('event_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('evidence_references', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('performed_by', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_maintenance_asset', 'utility_maintenance_events', ['utility_asset_id'])
    op.create_index('idx_maintenance_event_type', 'utility_maintenance_events', ['event_type'])

    # 11. Subsurface Observations Table
    op.create_table(
        'subsurface_observations',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('source_type', sa.String(64), nullable=False, server_default='GPR'),
        sa.Column('acquisition_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('geometry_wkt', sa.Text(), nullable=True),
        sa.Column('depth_meters', sa.Float(), nullable=True),
        sa.Column('signal_reference', sa.String(128), nullable=True),
        sa.Column('processing_status', sa.String(32), nullable=False, server_default='RAW'),
        sa.Column('metadata_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_subsurface_obs_source', 'subsurface_observations', ['source_type'])


def downgrade() -> None:
    op.drop_table('subsurface_observations')
    op.drop_table('utility_maintenance_events')
    op.drop_table('utility_inspections')
    op.drop_table('utility_clashes')
    op.drop_table('utility_separation_rules')
    op.drop_table('utility_corridors')
    op.drop_table('utility_structures')
    op.drop_table('utility_segments')
    op.drop_table('utility_nodes')
    op.drop_table('utility_assets')
    op.drop_table('utility_networks')

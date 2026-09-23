"""Initial Schema: Organizations, Jurisdictions, Users, Tokens, Audit

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-22 20:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    # 1. Organizations
    op.create_table(
        'organizations',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('code', sa.String(64), nullable=False, unique=True),
        sa.Column('type', sa.String(64), nullable=False, server_default='MUNICIPALITY'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_organizations_code', 'organizations', ['code'])
    op.create_index('idx_organizations_name', 'organizations', ['name'])

    # 2. Jurisdictions
    boundary_col = (
        sa.Column('boundary', Geometry('MULTIPOLYGON', srid=4326, spatial_index=False), nullable=True)
        if is_postgres
        else sa.Column('boundary', sa.Text(), nullable=True)
    )

    op.create_table(
        'jurisdictions',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('organization_id', sa.CHAR(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('code', sa.String(64), nullable=False, unique=True),
        sa.Column('level', sa.String(64), nullable=False, server_default='WARD'),
        sa.Column('srid', sa.Integer(), nullable=False, server_default='4326'),
        boundary_col,
        sa.Column('boundary_wkt', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_jurisdictions_code', 'jurisdictions', ['code'])
    op.create_index('idx_jurisdictions_org_id', 'jurisdictions', ['organization_id'])

    # PostGIS GIST index for PostgreSQL
    if is_postgres:
        op.execute("CREATE INDEX idx_jurisdictions_boundary ON jurisdictions USING GIST (boundary);")

    # 3. Users
    op.create_table(
        'users',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('username', sa.String(100), nullable=False, unique=True),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(32), nullable=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(64), nullable=False, server_default='CITIZEN'),
        sa.Column('organization_id', sa.CHAR(36), sa.ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('jurisdiction_id', sa.CHAR(36), sa.ForeignKey('jurisdictions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_username', 'users', ['username'])
    op.create_index('idx_users_role', 'users', ['role'])

    # 4. Refresh Tokens
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('user_id', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(255), nullable=False, unique=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_refresh_tokens_hash', 'refresh_tokens', ['token_hash'])
    op.create_index('idx_refresh_tokens_user', 'refresh_tokens', ['user_id'])

    # 5. Audit Logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('actor_user_id', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(128), nullable=False),
        sa.Column('entity_type', sa.String(64), nullable=False),
        sa.Column('entity_id', sa.String(128), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(512), nullable=True),
        sa.Column('details', sa.JSON(), nullable=False),
    )
    op.create_index('idx_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('idx_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id'])
    op.create_index('idx_audit_logs_timestamp', 'audit_logs', ['timestamp'])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('refresh_tokens')
    op.drop_table('users')
    op.drop_table('jurisdictions')
    op.drop_table('organizations')

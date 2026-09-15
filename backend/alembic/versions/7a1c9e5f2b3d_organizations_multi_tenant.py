"""organizations (multi-tenant), users password/status/lockout, audit_logs org/ip/agent

Revision ID: 7a1c9e5f2b3d
Revises: 45ef9b253567
Create Date: 2026-09-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a1c9e5f2b3d'
down_revision: Union[str, None] = '45ef9b253567'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Deterministic id for the implicit tenant that every pre-existing row
# (campaigns, users) is backfilled into — AUTH_PROVIDER=local's single
# auto-created operator keeps using this same organization afterwards
# (see app/core/security.py::_get_or_create_local_organization), so a
# database that upgrades from V1/PROMPT 3 keeps working exactly as before.
DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_ORG_SLUG = "local"
DEFAULT_ORG_NAME = "Organização Local"


def upgrade() -> None:
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='ACTIVE'),
        sa.Column('owner_user_id', sa.String(length=36), nullable=True),
        sa.Column('plan', sa.String(length=50), nullable=False, server_default='standard'),
        sa.Column('storage_limit_bytes', sa.Integer(), nullable=True),
        sa.Column('settings_json', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_organizations_slug'), 'organizations', ['slug'], unique=True)

    op.execute(
        sa.text(
            "INSERT INTO organizations (id, created_at, updated_at, name, slug, status, plan) "
            "VALUES (:id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, :name, :slug, 'ACTIVE', 'standard')"
        ).bindparams(id=DEFAULT_ORG_ID, name=DEFAULT_ORG_NAME, slug=DEFAULT_ORG_SLUG)
    )

    # --- campaigns: organization_id (NOT NULL after backfill) --------------
    op.add_column('campaigns', sa.Column('organization_id', sa.String(length=36), nullable=True))
    op.execute(
        sa.text("UPDATE campaigns SET organization_id = :org_id WHERE organization_id IS NULL").bindparams(
            org_id=DEFAULT_ORG_ID
        )
    )
    with op.batch_alter_table('campaigns') as batch_op:
        batch_op.alter_column('organization_id', existing_type=sa.String(length=36), nullable=False)
        batch_op.create_foreign_key(
            'fk_campaigns_organization_id', 'organizations', ['organization_id'], ['id']
        )
        batch_op.create_index(op.f('ix_campaigns_organization_id'), ['organization_id'])

    # --- users: organization_id (nullable — NULL reserved for SUPER_ADMIN), --
    # --- password/status/lockout ------------------------------------------
    op.add_column('users', sa.Column('organization_id', sa.String(length=36), nullable=True))
    op.execute(
        sa.text("UPDATE users SET organization_id = :org_id WHERE organization_id IS NULL").bindparams(
            org_id=DEFAULT_ORG_ID
        )
    )
    op.add_column('users', sa.Column('status', sa.String(length=20), nullable=False, server_default='ACTIVE'))
    op.add_column('users', sa.Column('password_hash', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        'users', sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0')
    )
    op.add_column('users', sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True))
    with op.batch_alter_table('users') as batch_op:
        batch_op.create_foreign_key('fk_users_organization_id', 'organizations', ['organization_id'], ['id'])
        batch_op.create_index(op.f('ix_users_organization_id'), ['organization_id'])

    # --- audit_logs: organization_id, ip_address, user_agent (additive) ----
    op.add_column('audit_logs', sa.Column('organization_id', sa.String(length=36), nullable=True))
    op.add_column('audit_logs', sa.Column('ip_address', sa.String(length=64), nullable=True))
    op.add_column('audit_logs', sa.Column('user_agent', sa.String(length=500), nullable=True))
    op.create_index(op.f('ix_audit_logs_organization_id'), 'audit_logs', ['organization_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_logs_organization_id'), table_name='audit_logs')
    op.drop_column('audit_logs', 'user_agent')
    op.drop_column('audit_logs', 'ip_address')
    op.drop_column('audit_logs', 'organization_id')

    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_constraint('fk_users_organization_id', type_='foreignkey')
        batch_op.drop_index(op.f('ix_users_organization_id'))
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
    op.drop_column('users', 'last_login_at')
    op.drop_column('users', 'password_hash')
    op.drop_column('users', 'status')
    op.drop_column('users', 'organization_id')

    with op.batch_alter_table('campaigns') as batch_op:
        batch_op.drop_index(op.f('ix_campaigns_organization_id'))
        batch_op.drop_constraint('fk_campaigns_organization_id', type_='foreignkey')
        batch_op.alter_column('organization_id', existing_type=sa.String(length=36), nullable=True)
    op.drop_column('campaigns', 'organization_id')

    op.drop_index(op.f('ix_organizations_slug'), table_name='organizations')
    op.drop_table('organizations')

"""user_permissions (per-user grants for Role.CUSTOM)

Revision ID: 9b2d4f6a8c1e
Revises: 7a1c9e5f2b3d
Create Date: 2026-09-15 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9b2d4f6a8c1e'
down_revision: Union[str, None] = '7a1c9e5f2b3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_permissions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('permission', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'permission', name='uq_user_permissions_user_permission'),
    )
    op.create_index(op.f('ix_user_permissions_user_id'), 'user_permissions', ['user_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_user_permissions_user_id'), table_name='user_permissions')
    op.drop_table('user_permissions')

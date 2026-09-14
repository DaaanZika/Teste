"""compliance rule versioning (effective_from/until, supersedes_id)

Revision ID: 45ef9b253567
Revises: c075b2cd186e
Create Date: 2026-09-14 15:44:29.807289

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '45ef9b253567'
down_revision: Union[str, None] = 'c075b2cd186e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# `rule_id` moves from UNIQUE (one row per rule ever) to a plain index —
# many version-rows can now share a rule_id (see
# app/services/compliance/rule_registry.py). The old constraint was never
# given an explicit name in the model, so each dialect needs a different
# way to reach it: Postgres auto-named it `compliance_rules_rule_id_key`
# (checked against a real Postgres instance migrated through the previous
# revision, not assumed); SQLite's batch mode needs an explicitly-named
# `copy_from` table to have anything to reference at all — verified that
# `batch_op.drop_constraint(None, ...)` fails outright with "Constraint
# must have a name", and that `op.create_foreign_key`/`op.add_column`
# outside of batch mode fail on SQLite with "No support for ALTER of
# constraints" — so every SQLite change here happens inside one batch
# block instead of split auto-generated calls.
_old_table = sa.Table(
    'compliance_rules',
    sa.MetaData(),
    sa.Column('id', sa.String(length=36), primary_key=True),
    sa.Column('rule_id', sa.String(length=100), nullable=False),
    sa.Column('election_year', sa.Integer(), nullable=True),
    sa.Column('rule_name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('legal_source', sa.String(length=255), nullable=True),
    sa.Column('article', sa.String(length=50), nullable=True),
    sa.Column('paragraph', sa.String(length=50), nullable=True),
    sa.Column('inciso', sa.String(length=50), nullable=True),
    sa.Column('severity', sa.String(length=20), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('validation_logic', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.UniqueConstraint('rule_id', name='uq_compliance_rules_rule_id'),
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.drop_constraint('compliance_rules_rule_id_key', 'compliance_rules', type_='unique')
        op.add_column('compliance_rules', sa.Column('effective_from', sa.Date(), nullable=False))
        op.add_column('compliance_rules', sa.Column('effective_until', sa.Date(), nullable=True))
        op.add_column('compliance_rules', sa.Column('supersedes_id', sa.String(length=36), nullable=True))
        op.create_index(op.f('ix_compliance_rules_rule_id'), 'compliance_rules', ['rule_id'], unique=False)
        op.create_foreign_key(
            'compliance_rules_supersedes_id_fkey', 'compliance_rules', 'compliance_rules', ['supersedes_id'], ['id']
        )
    else:
        with op.batch_alter_table('compliance_rules', copy_from=_old_table) as batch_op:
            batch_op.drop_constraint('uq_compliance_rules_rule_id', type_='unique')
            batch_op.add_column(sa.Column('effective_from', sa.Date(), nullable=False))
            batch_op.add_column(sa.Column('effective_until', sa.Date(), nullable=True))
            batch_op.add_column(sa.Column('supersedes_id', sa.String(length=36), nullable=True))
            batch_op.create_index(op.f('ix_compliance_rules_rule_id'), ['rule_id'], unique=False)
            batch_op.create_foreign_key(
                'fk_compliance_rules_supersedes_id', 'compliance_rules', ['supersedes_id'], ['id']
            )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.drop_constraint('compliance_rules_supersedes_id_fkey', 'compliance_rules', type_='foreignkey')
        op.drop_index(op.f('ix_compliance_rules_rule_id'), table_name='compliance_rules')
        op.drop_column('compliance_rules', 'supersedes_id')
        op.drop_column('compliance_rules', 'effective_until')
        op.drop_column('compliance_rules', 'effective_from')
        op.create_unique_constraint('compliance_rules_rule_id_key', 'compliance_rules', ['rule_id'])
    else:
        with op.batch_alter_table('compliance_rules') as batch_op:
            batch_op.drop_constraint('fk_compliance_rules_supersedes_id', type_='foreignkey')
            batch_op.drop_index(op.f('ix_compliance_rules_rule_id'))
            batch_op.drop_column('supersedes_id')
            batch_op.drop_column('effective_until')
            batch_op.drop_column('effective_from')
            batch_op.create_unique_constraint('uq_compliance_rules_rule_id', ['rule_id'])

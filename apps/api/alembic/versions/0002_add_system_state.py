"""add system_state table for atomic setup locking

Revision ID: 0002_add_system_state
Revises: 0001_initial_users
Create Date: 2026-11-04 07:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0002_add_system_state'
down_revision: Union[str, None] = '0001_initial_users'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'system_state',
        sa.Column('key', sa.String(length=50), nullable=False),
        sa.Column('value', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('key')
    )
    op.create_index(op.f('ix_system_state_key'), 'system_state', ['key'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_system_state_key'), table_name='system_state')
    op.drop_table('system_state')

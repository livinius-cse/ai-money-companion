"""add ai_disclosure_attestations table

Revision ID: 0003_add_ai_disclosure_attestation
Revises: 0002_add_system_state
Create Date: 2026-11-04 15:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0003_add_ai_disclosure_attestation'
down_revision: Union[str, None] = '0002_add_system_state'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ai_disclosure_attestations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('disclosure_version', sa.String(length=20), nullable=False),
        sa.Column('text_creation_method', sa.String(length=20), nullable=False),
        sa.Column('text_tools_used', sa.JSON(), nullable=False),
        sa.Column('text_editing_extent', sa.String(length=30), nullable=True),
        sa.Column('image_creation_method', sa.String(length=20), nullable=False),
        sa.Column('image_tools_used', sa.JSON(), nullable=False),
        sa.Column('image_editing_extent', sa.String(length=30), nullable=True),
        sa.Column('translation_creation_method', sa.String(length=20), nullable=False),
        sa.Column('translation_tools_used', sa.JSON(), nullable=False),
        sa.Column('translation_editing_extent', sa.String(length=30), nullable=True),
        sa.Column('kdp_submission_declaration', sa.Text(), nullable=False),
        sa.Column('author_reviewed', sa.Boolean(), nullable=False),
        sa.Column('author_attested_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_disclosure_attestations_id'), 'ai_disclosure_attestations', ['id'], unique=False)
    op.create_index(op.f('ix_ai_disclosure_attestations_user_id'), 'ai_disclosure_attestations', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ai_disclosure_attestations_user_id'), table_name='ai_disclosure_attestations')
    op.drop_index(op.f('ix_ai_disclosure_attestations_id'), table_name='ai_disclosure_attestations')
    op.drop_table('ai_disclosure_attestations')

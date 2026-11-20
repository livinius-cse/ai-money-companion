"""create m5 book_approval_snapshots table

Revision ID: 0006_create_m5_approval_snapshots
Revises: 0005_create_m4_book_documents_table
Create Date: 2026-11-20 16:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0006_create_m5_approval_snapshots'
down_revision: Union[str, None] = '0005_create_m4_book_documents_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'book_approval_snapshots',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('book_id', sa.String(length=36), nullable=False),
        sa.Column('owner_id', sa.String(length=36), nullable=False),
        sa.Column('approving_user_id', sa.String(length=36), nullable=False),
        sa.Column('snapshot_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='ACTIVE'),
        sa.Column('manuscript_hash', sa.String(length=64), nullable=False),
        sa.Column('metadata_hash', sa.String(length=64), nullable=False),
        sa.Column('interior_hash', sa.String(length=64), nullable=False),
        sa.Column('cover_hash', sa.String(length=64), nullable=False),
        sa.Column('composite_hash', sa.String(length=64), nullable=False),
        sa.Column('hash_scheme_version', sa.String(length=30), nullable=False, server_default='kdp-sha256-v1'),
        sa.Column('interior_document_id', sa.String(length=36), nullable=True),
        sa.Column('interior_document_version', sa.Integer(), nullable=True),
        sa.Column('cover_document_id', sa.String(length=36), nullable=True),
        sa.Column('cover_document_version', sa.Integer(), nullable=True),
        sa.Column('qa_report_id', sa.String(length=36), nullable=True),
        sa.Column('qa_report_summary', sa.JSON(), nullable=True),
        sa.Column('approval_attestation', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('invalidated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('invalidation_reason', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approving_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_book_approval_snapshots_id'), 'book_approval_snapshots', ['id'], unique=False)
    op.create_index(op.f('ix_book_approval_snapshots_book_id'), 'book_approval_snapshots', ['book_id'], unique=False)
    op.create_index(op.f('ix_book_approval_snapshots_owner_id'), 'book_approval_snapshots', ['owner_id'], unique=False)
    op.create_index(op.f('ix_book_approval_snapshots_approving_user_id'), 'book_approval_snapshots', ['approving_user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_book_approval_snapshots_approving_user_id'), table_name='book_approval_snapshots')
    op.drop_index(op.f('ix_book_approval_snapshots_owner_id'), table_name='book_approval_snapshots')
    op.drop_index(op.f('ix_book_approval_snapshots_book_id'), table_name='book_approval_snapshots')
    op.drop_index(op.f('ix_book_approval_snapshots_id'), table_name='book_approval_snapshots')
    op.drop_table('book_approval_snapshots')

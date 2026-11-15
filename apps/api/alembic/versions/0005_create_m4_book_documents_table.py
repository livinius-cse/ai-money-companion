"""create m4 book_documents table (interior and cover pdfs)

Revision ID: 0005_create_m4_book_documents_table
Revises: 0004_create_m3_product_studio_tables
Create Date: 2026-11-13 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0005_create_m4_book_documents_table'
down_revision: Union[str, None] = '0004_create_m3_product_studio_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'book_documents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('owner_id', sa.String(length=36), nullable=False),
        sa.Column('book_id', sa.String(length=36), nullable=False),
        sa.Column('document_type', sa.String(length=20), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('storage_key', sa.String(length=255), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False, server_default='application/pdf'),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sha256_hash', sa.String(length=64), nullable=False),
        sa.Column('page_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('width_pt', sa.Float(), nullable=False),
        sa.Column('height_pt', sa.Float(), nullable=False),
        sa.Column('trim_size', sa.String(length=30), nullable=False),
        sa.Column('bleed_config', sa.String(length=50), nullable=False, server_default='no_bleed'),
        sa.Column('source_book_version', sa.String(length=50), nullable=True),
        sa.Column('generation_metadata', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='PENDING'),
        sa.Column('error_message', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_book_documents_id'), 'book_documents', ['id'], unique=False)
    op.create_index(op.f('ix_book_documents_owner_id'), 'book_documents', ['owner_id'], unique=False)
    op.create_index(op.f('ix_book_documents_book_id'), 'book_documents', ['book_id'], unique=False)
    op.create_index(op.f('ix_book_documents_document_type'), 'book_documents', ['document_type'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_book_documents_document_type'), table_name='book_documents')
    op.drop_index(op.f('ix_book_documents_book_id'), table_name='book_documents')
    op.drop_index(op.f('ix_book_documents_owner_id'), table_name='book_documents')
    op.drop_index(op.f('ix_book_documents_id'), table_name='book_documents')
    op.drop_table('book_documents')

"""create m3 product studio tables (books, chapters, illustrations)

Revision ID: 0004_create_m3_product_studio_tables
Revises: 0003_add_ai_disclosure_attestation
Create Date: 2026-11-06 21:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0004_create_m3_product_studio_tables'
down_revision: Union[str, None] = '0003_add_ai_disclosure_attestation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Books table
    op.create_table(
        'books',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('owner_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('subtitle', sa.String(length=255), nullable=True),
        sa.Column('topic', sa.Text(), nullable=False),
        sa.Column('book_concept', sa.Text(), nullable=True),
        sa.Column('target_audience', sa.String(length=255), nullable=True),
        sa.Column('target_reader_profile', sa.Text(), nullable=True),
        sa.Column('book_type', sa.String(length=50), nullable=False, server_default='non_fiction'),
        sa.Column('print_format', sa.String(length=20), nullable=False, server_default='paperback'),
        sa.Column('marketplace', sa.String(length=50), nullable=False, server_default='amazon_com'),
        sa.Column('trim_size', sa.String(length=30), nullable=False, server_default='6x9'),
        sa.Column('paper_type', sa.String(length=50), nullable=False, server_default='white_bw'),
        sa.Column('target_page_count', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='DRAFT'),
        sa.Column('front_matter_pages', sa.Integer(), nullable=False, server_default='4'),
        sa.Column('back_matter_pages', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_books_id'), 'books', ['id'], unique=False)
    op.create_index(op.f('ix_books_owner_id'), 'books', ['owner_id'], unique=False)

    # 2. Chapters table
    op.create_table(
        'chapters',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('book_id', sa.String(length=36), nullable=False),
        sa.Column('owner_id', sa.String(length=36), nullable=False),
        sa.Column('chapter_number', sa.Integer(), nullable=False),
        sa.Column('chapter_type', sa.String(length=30), nullable=False, server_default='chapter'),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False, server_default=''),
        sa.Column('allocated_pages', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('word_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('draft_status', sa.String(length=30), nullable=False, server_default='NOT_STARTED'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chapters_id'), 'chapters', ['id'], unique=False)
    op.create_index(op.f('ix_chapters_book_id'), 'chapters', ['book_id'], unique=False)
    op.create_index(op.f('ix_chapters_owner_id'), 'chapters', ['owner_id'], unique=False)
    op.create_index(op.f('ix_chapters_chapter_number'), 'chapters', ['chapter_number'], unique=False)

    # 3. Illustrations table
    op.create_table(
        'illustrations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('book_id', sa.String(length=36), nullable=False),
        sa.Column('chapter_id', sa.String(length=36), nullable=True),
        sa.Column('owner_id', sa.String(length=36), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('style_preset', sa.String(length=100), nullable=True),
        sa.Column('seed', sa.String(length=50), nullable=True),
        sa.Column('position_description', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='PROMPT'),
        sa.Column('storage_key', sa.String(length=255), nullable=True),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('sha256_hash', sa.String(length=64), nullable=True),
        sa.Column('asset_source', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['chapter_id'], ['chapters.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_illustrations_id'), 'illustrations', ['id'], unique=False)
    op.create_index(op.f('ix_illustrations_book_id'), 'illustrations', ['book_id'], unique=False)
    op.create_index(op.f('ix_illustrations_chapter_id'), 'illustrations', ['chapter_id'], unique=False)
    op.create_index(op.f('ix_illustrations_owner_id'), 'illustrations', ['owner_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_illustrations_owner_id'), table_name='illustrations')
    op.drop_index(op.f('ix_illustrations_chapter_id'), table_name='illustrations')
    op.drop_index(op.f('ix_illustrations_book_id'), table_name='illustrations')
    op.drop_index(op.f('ix_illustrations_id'), table_name='illustrations')
    op.drop_table('illustrations')

    op.drop_index(op.f('ix_chapters_chapter_number'), table_name='chapters')
    op.drop_index(op.f('ix_chapters_owner_id'), table_name='chapters')
    op.drop_index(op.f('ix_chapters_book_id'), table_name='chapters')
    op.drop_index(op.f('ix_chapters_id'), table_name='chapters')
    op.drop_table('chapters')

    op.drop_index(op.f('ix_books_owner_id'), table_name='books')
    op.drop_index(op.f('ix_books_id'), table_name='books')
    op.drop_table('books')

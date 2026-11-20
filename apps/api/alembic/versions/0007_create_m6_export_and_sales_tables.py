"""create m6 export and sales intelligence tables

Revision ID: 0007_create_m6_export_and_sales_tables
Revises: 0006_create_m5_approval_snapshots
Create Date: 2026-11-20 17:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0007_create_m6_export_and_sales_tables'
down_revision: Union[str, None] = '0006_create_m5_approval_snapshots'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. KDP Export Packages Table
    op.create_table(
        'kdp_export_packages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('book_id', sa.String(length=36), nullable=False),
        sa.Column('owner_id', sa.String(length=36), nullable=False),
        sa.Column('approval_snapshot_id', sa.String(length=36), nullable=True),
        sa.Column('export_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('storage_key', sa.String(length=255), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sha256_hash', sa.String(length=64), nullable=False),
        sa.Column('manifest_data', sa.JSON(), nullable=False),
        sa.Column('download_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['approval_snapshot_id'], ['book_approval_snapshots.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_kdp_export_packages_id'), 'kdp_export_packages', ['id'], unique=False)
    op.create_index(op.f('ix_kdp_export_packages_book_id'), 'kdp_export_packages', ['book_id'], unique=False)
    op.create_index(op.f('ix_kdp_export_packages_owner_id'), 'kdp_export_packages', ['owner_id'], unique=False)
    op.create_index(op.f('ix_kdp_export_packages_approval_snapshot_id'), 'kdp_export_packages', ['approval_snapshot_id'], unique=False)

    # 2. Sales Import Batches Table
    op.create_table(
        'sales_import_batches',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('owner_id', sa.String(length=36), nullable=False),
        sa.Column('book_id', sa.String(length=36), nullable=True),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('sanitized_filename', sa.String(length=255), nullable=False),
        sa.Column('storage_key', sa.String(length=255), nullable=False),
        sa.Column('reporting_period', sa.String(length=50), nullable=True),
        sa.Column('marketplace', sa.String(length=50), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=True),
        sa.Column('source_sha256', sa.String(length=64), nullable=False),
        sa.Column('row_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('provenance', sa.String(length=50), nullable=False, server_default='REAL_KDP_REPORT'),
        sa.Column('validation_result', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='VALID'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sales_import_batches_id'), 'sales_import_batches', ['id'], unique=False)
    op.create_index(op.f('ix_sales_import_batches_owner_id'), 'sales_import_batches', ['owner_id'], unique=False)
    op.create_index(op.f('ix_sales_import_batches_book_id'), 'sales_import_batches', ['book_id'], unique=False)

    # 3. Sales Records Table
    op.create_table(
        'sales_records',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('batch_id', sa.String(length=36), nullable=False),
        sa.Column('owner_id', sa.String(length=36), nullable=False),
        sa.Column('book_id', sa.String(length=36), nullable=True),
        sa.Column('transaction_date', sa.String(length=30), nullable=False),
        sa.Column('asin_isbn', sa.String(length=50), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('author', sa.String(length=255), nullable=True),
        sa.Column('marketplace', sa.String(length=50), nullable=False),
        sa.Column('format', sa.String(length=30), nullable=False, server_default='Paperback'),
        sa.Column('units_sold', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('units_refunded', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('net_units', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column('royalty_amount', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('provenance', sa.String(length=50), nullable=False, server_default='REAL_KDP_REPORT'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['sales_import_batches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sales_records_id'), 'sales_records', ['id'], unique=False)
    op.create_index(op.f('ix_sales_records_batch_id'), 'sales_records', ['batch_id'], unique=False)
    op.create_index(op.f('ix_sales_records_owner_id'), 'sales_records', ['owner_id'], unique=False)
    op.create_index(op.f('ix_sales_records_book_id'), 'sales_records', ['book_id'], unique=False)
    op.create_index(op.f('ix_sales_records_transaction_date'), 'sales_records', ['transaction_date'], unique=False)
    op.create_index(op.f('ix_sales_records_marketplace'), 'sales_records', ['marketplace'], unique=False)
    op.create_index(op.f('ix_sales_records_currency'), 'sales_records', ['currency'], unique=False)
    op.create_index(op.f('ix_sales_records_provenance'), 'sales_records', ['provenance'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_sales_records_provenance'), table_name='sales_records')
    op.drop_index(op.f('ix_sales_records_currency'), table_name='sales_records')
    op.drop_index(op.f('ix_sales_records_marketplace'), table_name='sales_records')
    op.drop_index(op.f('ix_sales_records_transaction_date'), table_name='sales_records')
    op.drop_index(op.f('ix_sales_records_book_id'), table_name='sales_records')
    op.drop_index(op.f('ix_sales_records_owner_id'), table_name='sales_records')
    op.drop_index(op.f('ix_sales_records_batch_id'), table_name='sales_records')
    op.drop_index(op.f('ix_sales_records_id'), table_name='sales_records')
    op.drop_table('sales_records')

    op.drop_index(op.f('ix_sales_import_batches_book_id'), table_name='sales_import_batches')
    op.drop_index(op.f('ix_sales_import_batches_owner_id'), table_name='sales_import_batches')
    op.drop_index(op.f('ix_sales_import_batches_id'), table_name='sales_import_batches')
    op.drop_table('sales_import_batches')

    op.drop_index(op.f('ix_kdp_export_packages_approval_snapshot_id'), table_name='kdp_export_packages')
    op.drop_index(op.f('ix_kdp_export_packages_owner_id'), table_name='kdp_export_packages')
    op.drop_index(op.f('ix_kdp_export_packages_book_id'), table_name='kdp_export_packages')
    op.drop_index(op.f('ix_kdp_export_packages_id'), table_name='kdp_export_packages')
    op.drop_table('kdp_export_packages')

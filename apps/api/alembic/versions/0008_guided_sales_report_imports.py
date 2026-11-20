"""support guided, report-specific sales imports

Revision ID: 0008_guided_sales_report_imports
Revises: 0007_create_m6_export_and_sales_tables
Create Date: 2026-11-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0008_guided_sales_report_imports"
down_revision: Union[str, None] = "0007_create_m6_export_and_sales_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("sales_import_batches") as batch:
        batch.add_column(
            sa.Column(
                "report_type",
                sa.String(length=50),
                nullable=False,
                server_default="LEGACY",
            )
        )
        batch.add_column(sa.Column("source_headers", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("column_mapping", sa.JSON(), nullable=True))
        batch.create_index(
            op.f("ix_sales_import_batches_report_type"),
            ["report_type"],
            unique=False,
        )

    with op.batch_alter_table("sales_records") as records:
        records.add_column(
            sa.Column(
                "report_type",
                sa.String(length=50),
                nullable=False,
                server_default="LEGACY",
            )
        )
        records.add_column(
            sa.Column("paid_units", sa.Integer(), nullable=False, server_default="0")
        )
        records.add_column(
            sa.Column("free_units", sa.Integer(), nullable=False, server_default="0")
        )
        records.add_column(
            sa.Column("kenp_read_pages", sa.Integer(), nullable=False, server_default="0")
        )
        records.alter_column(
            "format",
            existing_type=sa.String(length=30),
            nullable=True,
        )
        records.alter_column(
            "currency",
            existing_type=sa.String(length=10),
            nullable=True,
        )
        records.create_index(
            op.f("ix_sales_records_report_type"),
            ["report_type"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    report_rows = bind.execute(
        sa.text(
            "SELECT "
            "(SELECT COUNT(*) FROM sales_records WHERE report_type != 'LEGACY') + "
            "(SELECT COUNT(*) FROM sales_import_batches WHERE report_type != 'LEGACY') + "
            "(SELECT COUNT(*) FROM sales_records WHERE currency IS NULL OR format IS NULL)"
        )
    ).scalar_one()
    if report_rows:
        raise RuntimeError(
            "Cannot downgrade guided sales report support while report-specific data would be lost."
        )

    with op.batch_alter_table("sales_records") as records:
        records.drop_index(op.f("ix_sales_records_report_type"))
        records.alter_column(
            "currency",
            existing_type=sa.String(length=10),
            nullable=False,
        )
        records.alter_column(
            "format",
            existing_type=sa.String(length=30),
            nullable=False,
        )
        records.drop_column("kenp_read_pages")
        records.drop_column("free_units")
        records.drop_column("paid_units")
        records.drop_column("report_type")

    with op.batch_alter_table("sales_import_batches") as batch:
        batch.drop_index(op.f("ix_sales_import_batches_report_type"))
        batch.drop_column("column_mapping")
        batch.drop_column("source_headers")
        batch.drop_column("report_type")

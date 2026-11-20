"""make confirmed sales imports idempotent under concurrency

Revision ID: 0009_unique_sales_import_source
Revises: 0008_guided_sales_report_imports
Create Date: 2026-11-21 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0009_unique_sales_import_source"
down_revision: Union[str, None] = "0008_guided_sales_report_imports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    duplicate_count = op.get_bind().execute(
        sa.text(
            "SELECT COUNT(*) FROM ("
            "SELECT owner_id, book_id, report_type, provenance, source_sha256 "
            "FROM sales_import_batches "
            "WHERE book_id IS NOT NULL "
            "GROUP BY owner_id, book_id, report_type, provenance, source_sha256 "
            "HAVING COUNT(*) > 1"
            ")"
        )
    ).scalar_one()
    if duplicate_count:
        raise RuntimeError(
            "Cannot add the sales import idempotency index while duplicate source batches exist."
        )

    op.create_index(
        "uq_sales_import_source",
        "sales_import_batches",
        ["owner_id", "book_id", "report_type", "provenance", "source_sha256"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_sales_import_source", table_name="sales_import_batches")

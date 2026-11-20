"""leave non-royalty report amounts unset

Revision ID: 0010_nullable_unreported_royalties
Revises: 0009_unique_sales_import_source
Create Date: 2026-11-21 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0010_nullable_unreported_royalties"
down_revision: Union[str, None] = "0009_unique_sales_import_source"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("sales_records") as records:
        records.alter_column(
            "royalty_amount",
            existing_type=sa.Float(),
            nullable=True,
        )


def downgrade() -> None:
    null_amount_count = op.get_bind().execute(
        sa.text("SELECT COUNT(*) FROM sales_records WHERE royalty_amount IS NULL")
    ).scalar_one()
    if null_amount_count:
        raise RuntimeError(
            "Cannot downgrade nullable royalties while non-royalty report rows are present."
        )

    with op.batch_alter_table("sales_records") as records:
        records.alter_column(
            "royalty_amount",
            existing_type=sa.Float(),
            nullable=False,
        )

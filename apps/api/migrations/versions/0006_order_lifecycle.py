"""pharmacy order lifecycle

Revision ID: 0006_order_lifecycle
Revises: 0005_consultation_notes
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_order_lifecycle"
down_revision: str | None = "0005_consultation_notes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW = [
    "TO_VERIFY",
    "PREPARING",
    "VERIFIED",
    "OUT_FOR_DELIVERY",
    "DELIVERED",
    "COMPLETED",
    "CANCELLED",
]


def upgrade() -> None:
    op.add_column(
        "pharmacy_offers", sa.Column("order_no", sa.String(), nullable=False, server_default="")
    )
    op.create_index("ix_pharmacy_offers_order_no", "pharmacy_offers", ["order_no"])
    with op.get_context().autocommit_block():
        for v in _NEW:
            op.execute(f"ALTER TYPE offer_status ADD VALUE IF NOT EXISTS '{v}'")


def downgrade() -> None:
    op.drop_index("ix_pharmacy_offers_order_no", table_name="pharmacy_offers")
    op.drop_column("pharmacy_offers", "order_no")
    # Postgres cannot drop enum values; the added labels remain.

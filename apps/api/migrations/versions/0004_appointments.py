"""appointment scheduling

Revision ID: 0004_appointments
Revises: 0003_medicines
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_appointments"
down_revision: str | None = "0003_medicines"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "consultations", sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True)
    )
    # ALTER TYPE ... ADD VALUE cannot run inside the migration transaction.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE consultation_status ADD VALUE IF NOT EXISTS 'ARRIVED'")


def downgrade() -> None:
    # Postgres cannot drop an enum value; leave 'ARRIVED' in place.
    op.drop_column("consultations", "scheduled_at")

"""medicine catalog

Revision ID: 0003_medicines
Revises: 0002_labs_and_constraints
Create Date: 2026-10-19
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_medicines"
down_revision: str | None = "0002_labs_and_constraints"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "medicines",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("strength", sa.String(), nullable=False, server_default=""),
        sa.Column("form", sa.String(), nullable=False, server_default="tablet"),
        sa.Column("is_common", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_medicines_name", "medicines", ["name"])


def downgrade() -> None:
    op.drop_index("ix_medicines_name", table_name="medicines")
    op.drop_table("medicines")

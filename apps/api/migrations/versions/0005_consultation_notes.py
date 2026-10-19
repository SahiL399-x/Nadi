"""consultation notes

Revision ID: 0005_consultation_notes
Revises: 0004_appointments
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_consultation_notes"
down_revision: str | None = "0004_appointments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "consultation_notes",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "consultation_id", sa.UUID(), sa.ForeignKey("consultations.id"), nullable=False
        ),
        sa.Column("author_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("consultation_notes")

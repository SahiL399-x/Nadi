"""patient medical history

Revision ID: 0007_patient_history
Revises: 0006_order_lifecycle
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_patient_history"
down_revision: str | None = "0006_order_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "patient_conditions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("patient_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
    )
    op.create_table(
        "patient_visits",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("patient_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("consultation_id", sa.UUID(), sa.ForeignKey("consultations.id"), nullable=True),
        sa.Column("visited_at", sa.String(), nullable=False),
        sa.Column("summary", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="Completed"),
    )


def downgrade() -> None:
    op.drop_table("patient_visits")
    op.drop_table("patient_conditions")

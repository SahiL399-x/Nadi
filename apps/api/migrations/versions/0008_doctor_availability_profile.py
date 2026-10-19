"""doctor availability and profile fields

Revision ID: 0008_doctor_availability_profile
Revises: 0007_patient_history
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_doctor_availability_profile"
down_revision: str | None = "0007_patient_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "doctors", sa.Column("clinic_address", sa.String(), nullable=False, server_default="")
    )
    op.add_column("doctors", sa.Column("about", sa.String(), nullable=False, server_default=""))
    op.create_table(
        "doctor_availability",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("doctor_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("morning", sa.String(), nullable=False, server_default="09:00-13:00"),
        sa.Column("evening", sa.String(), nullable=False, server_default="17:00-20:00"),
        sa.Column("is_open", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_table("doctor_availability")
    op.drop_column("doctors", "about")
    op.drop_column("doctors", "clinic_address")

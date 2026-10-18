"""persist triage labs and add uniqueness guards

Revision ID: 0002_labs_and_constraints
Revises: 0001_initial
Create Date: 2026-10-18

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_labs_and_constraints"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Persist the lab panel extracted at intake so it reaches the doctor/patient.
    op.add_column(
        "triage_results",
        sa.Column("labs", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    # One triage result per consultation; surfaces accidental double-intake writes.
    op.create_unique_constraint(
        "uq_triage_results_consultation_id", "triage_results", ["consultation_id"]
    )
    # A pharmacy is offered a given prescription at most once (no duplicate inbox rows).
    op.create_unique_constraint(
        "uq_pharmacy_offers_prescription_pharmacy",
        "pharmacy_offers",
        ["prescription_id", "pharmacy_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_pharmacy_offers_prescription_pharmacy", "pharmacy_offers", type_="unique"
    )
    op.drop_constraint(
        "uq_triage_results_consultation_id", "triage_results", type_="unique"
    )
    op.drop_column("triage_results", "labs")

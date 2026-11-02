"""drop acuity, acuity_confidence, red_flags, drivers from triage_results

Revision ID: 0010_drop_acuity
Revises: 0009_report_extraction_json
Create Date: 2026-11-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM, JSONB

revision: str = "0010_drop_acuity"
down_revision: str | None = "0009_report_extraction_json"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("triage_results", "acuity")
    op.drop_column("triage_results", "acuity_confidence")
    op.drop_column("triage_results", "red_flags")
    op.drop_column("triage_results", "drivers")
    ENUM(name="acuity").drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    acuity = ENUM("ROUTINE", "PRIORITY", "URGENT", "EMERGENCY", name="acuity")
    acuity.create(op.get_bind(), checkfirst=True)
    op.add_column("triage_results", sa.Column("acuity", acuity, nullable=True))
    op.add_column("triage_results", sa.Column("acuity_confidence", sa.Float(), nullable=True))
    op.add_column("triage_results", sa.Column("red_flags", JSONB(), nullable=True))
    op.add_column("triage_results", sa.Column("drivers", JSONB(), nullable=True))

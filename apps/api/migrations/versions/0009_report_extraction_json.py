"""report extraction_json

Revision ID: 0009_report_extraction_json
Revises: 0008_doctor_availability_profile
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_report_extraction_json"
down_revision: str | None = "0008_doctor_availability_profile"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("extraction_json", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("reports", "extraction_json")

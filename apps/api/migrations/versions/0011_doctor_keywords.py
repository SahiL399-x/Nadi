"""doctor keywords

Revision ID: 0011_doctor_keywords
Revises: 0010_drop_acuity
Create Date: 2026-11-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY

revision: str = "0011_doctor_keywords"
down_revision: str | None = "0010_drop_acuity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "doctors",
        sa.Column("keywords", ARRAY(sa.String()), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("doctors", "keywords")

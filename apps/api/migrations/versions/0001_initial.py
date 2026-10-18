"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-18

"""
from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("phone", sa.String(), nullable=False),
        sa.Column(
            "role",
            sa.Enum("patient", "doctor", "pharmacy", name="role"),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("lang", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_phone"), "users", ["phone"], unique=True)

    op.create_table(
        "audit_log",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("entity", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column(
            "at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "consultations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("patient_id", sa.UUID(), nullable=False),
        sa.Column("doctor_id", sa.UUID(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "TRIAGED",
                "BOOKED",
                "IN_PROGRESS",
                "DONE",
                name="consultation_status",
            ),
            nullable=False,
        ),
        sa.Column("booked_for", sa.String(), nullable=True),
        sa.Column("symptom_text_raw", sa.String(), nullable=False),
        sa.Column("symptom_text_normalised", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["doctor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "doctors",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("specialty", sa.String(), nullable=False),
        sa.Column("qualifications", sa.String(), nullable=False),
        sa.Column("reg_number", sa.String(), nullable=False),
        sa.Column("experience_years", sa.Integer(), nullable=False),
        sa.Column("fee_inr", sa.Integer(), nullable=False),
        sa.Column("languages", sa.ARRAY(sa.String()), nullable=False),
        sa.Column(
            "location",
            geoalchemy2.types.Geography(
                geometry_type="POINT",
                srid=4326,
                spatial_index=False,
                from_text="ST_GeogFromText",
                name="geography",
            ),
            nullable=True,
        ),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column("review_count", sa.Integer(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("photo_url", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(op.f("ix_doctors_specialty"), "doctors", ["specialty"], unique=False)

    op.create_table(
        "patients",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("sex", sa.String(), nullable=True),
        sa.Column(
            "location",
            geoalchemy2.types.Geography(
                geometry_type="POINT",
                srid=4326,
                spatial_index=False,
                from_text="ST_GeogFromText",
                name="geography",
            ),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "pharmacies",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("licence_number", sa.String(), nullable=False),
        sa.Column(
            "location",
            geoalchemy2.types.Geography(
                geometry_type="POINT",
                srid=4326,
                spatial_index=False,
                from_text="ST_GeogFromText",
                name="geography",
            ),
            nullable=True,
        ),
        sa.Column("delivers", sa.Boolean(), nullable=False),
        sa.Column("open_hours", sa.String(), nullable=False),
        sa.Column("is_open", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "prescriptions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("consultation_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "ACCEPTED",
                "DECLINED",
                "DELIVERED",
                name="prescription_status",
            ),
            nullable=False,
        ),
        sa.Column("superseded_by", sa.UUID(), nullable=True),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["consultation_id"], ["consultations.id"]),
        sa.ForeignKeyConstraint(["superseded_by"], ["prescriptions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "referrals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("consultation_id", sa.UUID(), nullable=False),
        sa.Column("from_doctor_id", sa.UUID(), nullable=False),
        sa.Column("to_specialty", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["consultation_id"], ["consultations.id"]),
        sa.ForeignKeyConstraint(["from_doctor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "reports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("consultation_id", sa.UUID(), nullable=False),
        sa.Column("object_key", sa.String(), nullable=False),
        sa.Column("ocr_status", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["consultation_id"], ["consultations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "triage_results",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("consultation_id", sa.UUID(), nullable=False),
        sa.Column(
            "acuity",
            sa.Enum("ROUTINE", "PRIORITY", "URGENT", "EMERGENCY", name="acuity"),
            nullable=False,
        ),
        sa.Column("acuity_confidence", sa.Float(), nullable=False),
        sa.Column("specialties", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("drivers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("red_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("model_version", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["consultation_id"], ["consultations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "lab_values",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("report_id", sa.UUID(), nullable=False),
        sa.Column("analyte", sa.String(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(), nullable=False),
        sa.Column("ref_range", sa.String(), nullable=False),
        sa.Column("flag", sa.Enum("L", "N", "H", name="lab_flag"), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "pharmacy_consents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("prescription_id", sa.UUID(), nullable=False),
        sa.Column("pharmacy_id", sa.UUID(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["pharmacy_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["prescription_id"], ["prescriptions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "pharmacy_offers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("prescription_id", sa.UUID(), nullable=False),
        sa.Column("pharmacy_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "ACCEPTED", "DECLINED", name="offer_status"),
            nullable=False,
        ),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("responded_at", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["pharmacy_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["prescription_id"], ["prescriptions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "prescription_lines",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("prescription_id", sa.UUID(), nullable=False),
        sa.Column("drug", sa.String(), nullable=False),
        sa.Column("strength", sa.String(), nullable=False),
        sa.Column("frequency", sa.String(), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("notes", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["prescription_id"], ["prescriptions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # GiST indexes on every location column (geography(Point, 4326)).
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_doctors_location ON doctors USING gist (location)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pharmacies_location ON pharmacies USING gist (location)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_patients_location ON patients USING gist (location)"
    )
    # Composite index for doctor schedule lookups.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_consult_doctor_status_booked "
        "ON consultations (doctor_id, status, booked_for)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS ix_consult_doctor_status_booked")
    op.execute("DROP INDEX IF EXISTS ix_patients_location")
    op.execute("DROP INDEX IF EXISTS ix_pharmacies_location")
    op.execute("DROP INDEX IF EXISTS ix_doctors_location")

    op.drop_table("prescription_lines")
    op.drop_table("pharmacy_offers")
    op.drop_table("pharmacy_consents")
    op.drop_table("lab_values")
    op.drop_table("triage_results")
    op.drop_table("reports")
    op.drop_table("referrals")
    op.drop_table("prescriptions")
    op.drop_table("pharmacies")
    op.drop_table("patients")
    op.drop_index(op.f("ix_doctors_specialty"), table_name="doctors")
    op.drop_table("doctors")
    op.drop_table("consultations")
    op.drop_table("audit_log")
    op.drop_index(op.f("ix_users_phone"), table_name="users")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS offer_status")
    op.execute("DROP TYPE IF EXISTS prescription_status")
    op.execute("DROP TYPE IF EXISTS lab_flag")
    op.execute("DROP TYPE IF EXISTS acuity")
    op.execute("DROP TYPE IF EXISTS consultation_status")
    op.execute("DROP TYPE IF EXISTS role")

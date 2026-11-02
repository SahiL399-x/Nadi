import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_col, uuid_pk


class TriageResult(Base):
    __tablename__ = "triage_results"
    id: Mapped[uuid.UUID] = uuid_pk()
    consultation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("consultations.id"))
    specialties = mapped_column(JSONB)      # [{name, score}]
    labs = mapped_column(JSONB)             # [LabValue] extracted from reports
    model_version: Mapped[str] = mapped_column(String)   # MANDATORY
    created_at: Mapped[datetime] = created_at_col()


class Referral(Base):
    __tablename__ = "referrals"
    id: Mapped[uuid.UUID] = uuid_pk()
    consultation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("consultations.id"))
    from_doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    to_specialty: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = created_at_col()

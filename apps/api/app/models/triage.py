import enum
import uuid

from sqlalchemy import Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_col, uuid_pk


class Acuity(str, enum.Enum):
    ROUTINE = "ROUTINE"
    PRIORITY = "PRIORITY"
    URGENT = "URGENT"
    EMERGENCY = "EMERGENCY"


class TriageResult(Base):
    __tablename__ = "triage_results"
    id: Mapped[uuid.UUID] = uuid_pk()
    consultation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("consultations.id"))
    acuity: Mapped[Acuity] = mapped_column(Enum(Acuity, name="acuity"))
    acuity_confidence: Mapped[float] = mapped_column(Float)
    specialties = mapped_column(JSONB)      # [{name, score}]
    drivers = mapped_column(JSONB)          # [{feature, contribution}]
    red_flags = mapped_column(JSONB)        # [str]
    model_version: Mapped[str] = mapped_column(String)   # MANDATORY
    created_at = created_at_col()


class Referral(Base):
    __tablename__ = "referrals"
    id: Mapped[uuid.UUID] = uuid_pk()
    consultation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("consultations.id"))
    from_doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    to_specialty: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(String)
    created_at = created_at_col()

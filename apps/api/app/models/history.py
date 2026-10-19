import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid_pk


class PatientCondition(Base):
    __tablename__ = "patient_conditions"
    id: Mapped[uuid.UUID] = uuid_pk()
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    label: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String)  # condition|allergy|family_history


class PatientVisit(Base):
    __tablename__ = "patient_visits"
    id: Mapped[uuid.UUID] = uuid_pk()
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    consultation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("consultations.id"), nullable=True
    )
    visited_at: Mapped[str] = mapped_column(String)  # ISO date for the demo
    summary: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="Completed")

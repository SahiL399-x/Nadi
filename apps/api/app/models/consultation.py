import enum
import uuid
from datetime import datetime

from sqlalchemy import Enum, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_col, uuid_pk


class ConsultationStatus(str, enum.Enum):
    PENDING = "PENDING"
    TRIAGED = "TRIAGED"
    BOOKED = "BOOKED"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


class Flag(str, enum.Enum):
    L = "L"
    N = "N"
    H = "H"


class Consultation(Base):
    __tablename__ = "consultations"
    id: Mapped[uuid.UUID] = uuid_pk()
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    doctor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[ConsultationStatus] = mapped_column(
        Enum(ConsultationStatus, name="consultation_status"),
        default=ConsultationStatus.PENDING,
    )
    booked_for: Mapped[str | None] = mapped_column(String, nullable=True)
    symptom_text_raw: Mapped[str] = mapped_column(String, default="")
    symptom_text_normalised: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = created_at_col()


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[uuid.UUID] = uuid_pk()
    consultation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("consultations.id"))
    object_key: Mapped[str] = mapped_column(String)
    ocr_status: Mapped[str] = mapped_column(String, default="pending")


class LabValue(Base):
    __tablename__ = "lab_values"
    id: Mapped[uuid.UUID] = uuid_pk()
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reports.id"))
    analyte: Mapped[str] = mapped_column(String)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String)
    ref_range: Mapped[str] = mapped_column(String)
    flag: Mapped[Flag] = mapped_column(Enum(Flag, name="lab_flag"))

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_col, uuid_pk


class PrescriptionStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    DELIVERED = "DELIVERED"


class OfferStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"


class Prescription(Base):
    __tablename__ = "prescriptions"
    id: Mapped[uuid.UUID] = uuid_pk()
    consultation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("consultations.id"))
    status: Mapped[PrescriptionStatus] = mapped_column(
        Enum(PrescriptionStatus, name="prescription_status"),
        default=PrescriptionStatus.PENDING,
    )
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("prescriptions.id"), nullable=True
    )
    issued_at = created_at_col()


class PrescriptionLine(Base):
    __tablename__ = "prescription_lines"
    id: Mapped[uuid.UUID] = uuid_pk()
    prescription_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("prescriptions.id"))
    drug: Mapped[str] = mapped_column(String)
    strength: Mapped[str] = mapped_column(String)
    frequency: Mapped[str] = mapped_column(String)
    duration_days: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)


class PharmacyConsent(Base):
    __tablename__ = "pharmacy_consents"
    id: Mapped[uuid.UUID] = uuid_pk()
    prescription_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("prescriptions.id"))
    pharmacy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    rank: Mapped[int] = mapped_column(Integer, default=0)  # routing order chosen by patient
    granted_at = created_at_col()


class PharmacyOffer(Base):
    __tablename__ = "pharmacy_offers"
    id: Mapped[uuid.UUID] = uuid_pk()
    prescription_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("prescriptions.id"))
    pharmacy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[OfferStatus] = mapped_column(
        Enum(OfferStatus, name="offer_status"), default=OfferStatus.PENDING
    )
    rank: Mapped[int] = mapped_column(Integer, default=0)
    responded_at: Mapped[str | None] = mapped_column(String, nullable=True)

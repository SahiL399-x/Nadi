import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid_pk


class DoctorAvailability(Base):
    __tablename__ = "doctor_availability"
    id: Mapped[uuid.UUID] = uuid_pk()
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    weekday: Mapped[int] = mapped_column(Integer)  # 0=Mon … 6=Sun
    morning: Mapped[str] = mapped_column(String, default="09:00-13:00")
    evening: Mapped[str] = mapped_column(String, default="17:00-20:00")
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)

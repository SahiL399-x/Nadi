import enum
import uuid

from geoalchemy2 import Geography
from sqlalchemy import ARRAY, Boolean, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_col, uuid_pk


class Role(str, enum.Enum):
    patient = "patient"
    doctor = "doctor"
    pharmacy = "pharmacy"


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = uuid_pk()
    phone: Mapped[str] = mapped_column(String, unique=True, index=True)
    role: Mapped[Role] = mapped_column(Enum(Role, name="role"))
    name: Mapped[str] = mapped_column(String)
    lang: Mapped[str] = mapped_column(String, default="en")
    created_at = created_at_col()


class Patient(Base):
    __tablename__ = "patients"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sex: Mapped[str | None] = mapped_column(String, nullable=True)
    location = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=True)


class Doctor(Base):
    __tablename__ = "doctors"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    specialty: Mapped[str] = mapped_column(String, index=True)
    qualifications: Mapped[str] = mapped_column(String)
    reg_number: Mapped[str] = mapped_column(String)
    experience_years: Mapped[int] = mapped_column(Integer, default=0)
    fee_inr: Mapped[int] = mapped_column(Integer, default=0)
    languages: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    location = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True)
    photo_url: Mapped[str] = mapped_column(String, default="")


class Pharmacy(Base):
    __tablename__ = "pharmacies"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    name: Mapped[str] = mapped_column(String)
    licence_number: Mapped[str] = mapped_column(String)
    location = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    delivers: Mapped[bool] = mapped_column(Boolean, default=True)
    open_hours: Mapped[str] = mapped_column(String, default="09:00-21:00")
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)

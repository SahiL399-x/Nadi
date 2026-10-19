import uuid

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid_pk


class Medicine(Base):
    __tablename__ = "medicines"
    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String, index=True)
    strength: Mapped[str] = mapped_column(String, default="")
    form: Mapped[str] = mapped_column(
        String, default="tablet"
    )  # tablet|capsule|syrup|drops|injection
    is_common: Mapped[bool] = mapped_column(Boolean, default=True)

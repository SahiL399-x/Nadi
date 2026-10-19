import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DoctorAvailability
from app.schemas.availability import AvailabilityOut

_DEFAULT = [(d, d < 5) for d in range(7)]  # Mon-Fri open, weekend closed


def get(db: Session, doctor_id) -> list[AvailabilityOut]:
    rows = {
        r.weekday: r
        for r in db.scalars(
            select(DoctorAvailability).where(DoctorAvailability.doctor_id == doctor_id)
        )
    }
    if not rows:  # lazily create defaults the first time
        for d, is_open in _DEFAULT:
            db.add(
                DoctorAvailability(id=uuid.uuid4(), doctor_id=doctor_id, weekday=d, is_open=is_open)
            )
        db.commit()
        rows = {
            r.weekday: r
            for r in db.scalars(
                select(DoctorAvailability).where(DoctorAvailability.doctor_id == doctor_id)
            )
        }
    return [
        AvailabilityOut(
            weekday=d, morning=rows[d].morning, evening=rows[d].evening, isOpen=rows[d].is_open
        )
        for d in range(7)
    ]


def put(db: Session, doctor_id, days: list[AvailabilityOut]) -> list[AvailabilityOut]:
    existing = {
        r.weekday: r
        for r in db.scalars(
            select(DoctorAvailability).where(DoctorAvailability.doctor_id == doctor_id)
        )
    }
    for d in days:
        row = existing.get(d.weekday)
        if row is None:
            row = DoctorAvailability(id=uuid.uuid4(), doctor_id=doctor_id, weekday=d.weekday)
            db.add(row)
        row.morning, row.evening, row.is_open = d.morning, d.evening, d.isOpen
    db.commit()
    return get(db, doctor_id)

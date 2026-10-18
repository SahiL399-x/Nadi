from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_SetSRID, ST_MakePoint
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Doctor, User
from app.schemas.doctor import DoctorOut

_SLOTS = ["09:00", "09:30", "10:00", "11:00", "14:00", "16:30"]


def _point(lat: float, lng: float):
    return func.cast(ST_SetSRID(ST_MakePoint(lng, lat), 4326), type_=Doctor.location.type)


def _to_out(doctor: Doctor, name: str, distance_km: float) -> DoctorOut:
    return DoctorOut(
        id=str(doctor.user_id), name=name, specialty=doctor.specialty,
        qualifications=doctor.qualifications, experienceYears=doctor.experience_years,
        distanceKm=round(distance_km, 1), feeInr=doctor.fee_inr, rating=doctor.rating,
        reviewCount=doctor.review_count, languages=list(doctor.languages),
        nextSlot=_SLOTS[0], photoUrl=doctor.photo_url, availableSlots=_SLOTS,
    )


def search(db: Session, specialty: str | None, lat: float, lng: float,
           radius_km: float, lang: str | None) -> list[DoctorOut]:
    pt = _point(lat, lng)
    dist = ST_Distance(Doctor.location, pt)
    stmt = select(Doctor, User.name, dist).join(User, User.id == Doctor.user_id)
    stmt = stmt.where(ST_DWithin(Doctor.location, pt, radius_km * 1000))
    if specialty:
        stmt = stmt.where(Doctor.specialty == specialty)
    if lang:
        stmt = stmt.where(Doctor.languages.any(lang))
    stmt = stmt.order_by(dist.asc())
    rows = db.execute(stmt).all()
    return [_to_out(d, name, d_m / 1000.0) for (d, name, d_m) in rows]


def get(db: Session, doctor_id: str) -> DoctorOut | None:
    row = db.execute(
        select(Doctor, User.name).join(User, User.id == Doctor.user_id)
        .where(Doctor.user_id == doctor_id)
    ).first()
    if row is None:
        return None
    doctor, name = row
    return _to_out(doctor, name, 0.0)

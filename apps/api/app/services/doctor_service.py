from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_MakePoint, ST_SetSRID
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Doctor, User
from app.schemas.doctor import DoctorOut
from app.schemas.doctor_profile import DoctorProfileOut

_SLOTS = ["09:00", "09:30", "10:00", "11:00", "14:00", "16:30"]

# Doctor.languages is stored as display names; the API filters by lang code.
_LANG_NAMES = {"en": "English", "hi": "Hindi", "mr": "Marathi"}


def _point(lat: float, lng: float):
    return func.cast(ST_SetSRID(ST_MakePoint(lng, lat), 4326), type_=Doctor.location.type)


def _to_out(doctor: Doctor, name: str, distance_km: float) -> DoctorOut:
    return DoctorOut(
        id=str(doctor.user_id),
        name=name,
        specialty=doctor.specialty,
        qualifications=doctor.qualifications,
        experienceYears=doctor.experience_years,
        distanceKm=round(distance_km, 1),
        feeInr=doctor.fee_inr,
        rating=doctor.rating,
        reviewCount=doctor.review_count,
        languages=list(doctor.languages),
        nextSlot=_SLOTS[0],
        photoUrl=doctor.photo_url,
        availableSlots=_SLOTS,
    )


def search(
    db: Session, specialty: str | None, lat: float, lng: float, radius_km: float, lang: str | None
) -> list[DoctorOut]:
    pt = _point(lat, lng)
    dist = ST_Distance(Doctor.location, pt)
    stmt = select(Doctor, User.name, dist).join(User, User.id == Doctor.user_id)
    stmt = stmt.where(ST_DWithin(Doctor.location, pt, radius_km * 1000))
    if specialty:
        stmt = stmt.where(Doctor.specialty == specialty)
    if lang:
        stmt = stmt.where(Doctor.languages.any(_LANG_NAMES.get(lang, lang)))
    stmt = stmt.order_by(dist.asc())
    rows = db.execute(stmt).all()
    return [_to_out(d, name, d_m / 1000.0) for (d, name, d_m) in rows]


def get(db: Session, doctor_id: str) -> DoctorOut | None:
    row = db.execute(
        select(Doctor, User.name)
        .join(User, User.id == Doctor.user_id)
        .where(Doctor.user_id == doctor_id)
    ).first()
    if row is None:
        return None
    doctor, name = row
    return _to_out(doctor, name, 0.0)


def profile(db: Session, doctor_id) -> DoctorProfileOut | None:
    doctor = db.get(Doctor, doctor_id)
    user = db.get(User, doctor_id)
    if doctor is None or user is None:
        return None
    return DoctorProfileOut(
        name=user.name,
        specialty=doctor.specialty,
        qualifications=doctor.qualifications,
        experienceYears=doctor.experience_years,
        clinicAddress=doctor.clinic_address,
        about=doctor.about,
        photoUrl=doctor.photo_url,
    )


def update_profile(db: Session, doctor_id, clinic_address, about):
    doctor = db.get(Doctor, doctor_id)
    if doctor is None:
        return None
    if clinic_address is not None:
        doctor.clinic_address = clinic_address
    if about is not None:
        doctor.about = about
    db.commit()
    return profile(db, doctor_id)

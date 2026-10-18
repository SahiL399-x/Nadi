from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.doctor import DoctorOut
from app.services import doctor_service

router = APIRouter(prefix="/v1/doctors", tags=["doctors"])


@router.get("", response_model=list[DoctorOut])
def search(specialty: str | None = None, lat: float = 19.9975, lng: float = 73.7898,
           radiusKm: float = 50.0, lang: str | None = None,
           db: Session = Depends(get_db)) -> list[DoctorOut]:
    return doctor_service.search(db, specialty, lat, lng, radiusKm, lang)


@router.get("/{doctor_id}", response_model=DoctorOut)
def get(doctor_id: str, db: Session = Depends(get_db)) -> DoctorOut:
    out = doctor_service.get(db, doctor_id)
    if out is None:
        raise HTTPException(status_code=404, detail="not found")
    return out

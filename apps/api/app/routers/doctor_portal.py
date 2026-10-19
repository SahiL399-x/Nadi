from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models import User
from app.schemas.appointment import AppointmentOut
from app.schemas.consultation import QueueItemOut
from app.schemas.prescription import PrescribeIn, ReferIn
from app.services import audit_service, consultation_service, prescription_service

router = APIRouter(prefix="/v1/doctor", tags=["doctor"])


@router.get("/queue", response_model=list[QueueItemOut])
def queue(user: User = Depends(require_role("doctor")), db: Session = Depends(get_db)):
    items = consultation_service.doctor_queue(db, user.id)
    audit_service.log(db, user.id, "view_queue", "doctor", str(user.id))
    return items


@router.get("/appointments", response_model=list[AppointmentOut])
def appointments(
    date: date | None = None,
    user: User = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
):
    return consultation_service.doctor_appointments(db, user.id, date)


@router.post("/consultations/{consultation_id}/refer")
def refer(
    consultation_id: str,
    body: ReferIn,
    user: User = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
) -> dict:
    if consultation_service.get_for_doctor(db, consultation_id, user.id) is None:
        raise HTTPException(status_code=404, detail="not found")
    prescription_service.refer(db, consultation_id, user.id, body.toSpecialty, body.reason)
    audit_service.log(db, user.id, "refer", "consultation", consultation_id)
    return {"referred": True}


@router.post("/consultations/{consultation_id}/prescribe")
def prescribe(
    consultation_id: str,
    body: PrescribeIn,
    user: User = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
) -> dict:
    if consultation_service.get_for_doctor(db, consultation_id, user.id) is None:
        raise HTTPException(status_code=404, detail="not found")
    pres = prescription_service.create(db, consultation_id, body.lines)
    audit_service.log(db, user.id, "prescribe", "consultation", consultation_id)
    return {"prescriptionId": str(pres.id)}

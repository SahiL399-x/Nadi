from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models import Consultation, ConsultationStatus, Patient, TriageResult, User
from app.schemas.common import TriageResultOut
from app.schemas.consultation import QueueItemOut
from app.schemas.prescription import PrescribeIn, ReferIn
from app.services import audit_service, prescription_service

router = APIRouter(prefix="/v1/doctor", tags=["doctor"])

_ORDER = {"EMERGENCY": 0, "URGENT": 1, "PRIORITY": 2, "ROUTINE": 3}


@router.get("/queue", response_model=list[QueueItemOut])
def queue(user: User = Depends(require_role("doctor")), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Consultation, TriageResult, User, Patient)
        .join(TriageResult, TriageResult.consultation_id == Consultation.id)
        .join(User, User.id == Consultation.patient_id)
        .join(Patient, Patient.user_id == Consultation.patient_id)
        .where(Consultation.doctor_id == user.id)
        .where(Consultation.status == ConsultationStatus.BOOKED)
    ).all()
    items = []
    for consult, tr, patient_user, patient in rows:
        acuity = tr.acuity.value if hasattr(tr.acuity, "value") else tr.acuity
        items.append(QueueItemOut(
            id=str(consult.id), patientName=patient_user.name, patientAge=patient.age or 0,
            patientSex=patient.sex or "O", acuity=acuity, complaint=consult.symptom_text_raw,
            bookedFor=consult.booked_for or "",
            triage=TriageResultOut(
                acuity=acuity, acuityConfidence=tr.acuity_confidence,
                specialties=tr.specialties, drivers=tr.drivers, labs=[],
                redFlags=tr.red_flags, modelVersion=tr.model_version,
            ),
        ))
    items.sort(key=lambda i: _ORDER[i.acuity])
    audit_service.log(db, user.id, "view_queue", "doctor", str(user.id))
    return items


@router.post("/consultations/{consultation_id}/refer")
def refer(consultation_id: str, body: ReferIn,
          user: User = Depends(require_role("doctor")), db: Session = Depends(get_db)) -> dict:
    prescription_service.refer(db, consultation_id, user.id, body.toSpecialty, body.reason)
    audit_service.log(db, user.id, "refer", "consultation", consultation_id)
    return {"referred": True}


@router.post("/consultations/{consultation_id}/prescribe")
def prescribe(consultation_id: str, body: PrescribeIn,
              user: User = Depends(require_role("doctor")), db: Session = Depends(get_db)) -> dict:
    pres = prescription_service.create(db, consultation_id, body.lines)
    audit_service.log(db, user.id, "prescribe", "consultation", consultation_id)
    return {"prescriptionId": str(pres.id)}

import uuid

from sqlalchemy.orm import Session

from app.models import Prescription, PrescriptionLine, Referral
from app.schemas.prescription import PrescriptionLineIn


def create(db: Session, consultation_id, lines: list[PrescriptionLineIn]) -> Prescription:
    pres = Prescription(id=uuid.uuid4(), consultation_id=consultation_id)
    db.add(pres)
    db.flush()
    for ln in lines:
        db.add(PrescriptionLine(
            id=uuid.uuid4(), prescription_id=pres.id, drug=ln.drug, strength=ln.strength,
            frequency=ln.frequency, duration_days=ln.durationDays, notes=ln.notes,
        ))
    db.commit()
    db.refresh(pres)
    return pres


def refer(db: Session, consultation_id, from_doctor_id, to_specialty: str, reason: str) -> Referral:
    ref = Referral(id=uuid.uuid4(), consultation_id=consultation_id,
                   from_doctor_id=from_doctor_id, to_specialty=to_specialty, reason=reason)
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return ref

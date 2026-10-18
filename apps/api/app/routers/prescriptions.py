from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_role
from app.models import Consultation, Prescription, PrescriptionLine, User
from app.schemas.prescription import ConsentIn, PrescriptionLineOut, PrescriptionOut
from app.services import audit_service, pharmacy_service

router = APIRouter(prefix="/v1/prescriptions", tags=["prescriptions"])


@router.get("/{prescription_id}", response_model=PrescriptionOut)
def get(prescription_id: str, user: User = Depends(get_current_user),
        db: Session = Depends(get_db)) -> PrescriptionOut:
    pres = db.get(Prescription, prescription_id)
    if pres is None:
        raise HTTPException(status_code=404, detail="not found")
    lines = db.scalars(
        select(PrescriptionLine).where(PrescriptionLine.prescription_id == pres.id)
    ).all()
    consult = db.get(Consultation, pres.consultation_id)
    patient = db.get(User, consult.patient_id)
    doctor = db.get(User, consult.doctor_id) if consult.doctor_id else None
    audit_service.log(db, user.id, "view_prescription", "prescription", prescription_id)
    return PrescriptionOut(
        id=str(pres.id), patientName=patient.name if patient else "",
        doctorName=doctor.name if doctor else "", issuedAt=str(pres.issued_at),
        lines=[PrescriptionLineOut(drug=ln.drug, strength=ln.strength, frequency=ln.frequency,
                                   durationDays=ln.duration_days, notes=ln.notes) for ln in lines],
        status=pres.status.value if hasattr(pres.status, "value") else pres.status,
    )


@router.post("/{prescription_id}/consent")
def consent(prescription_id: str, body: ConsentIn, user: User = Depends(require_role("patient")),
            db: Session = Depends(get_db)) -> dict:
    if not body.pharmacyIds:
        raise HTTPException(status_code=400, detail="at least one pharmacy required")
    pharmacy_service.grant_consent(db, prescription_id, body.pharmacyIds)
    audit_service.log(db, user.id, "consent", "prescription", prescription_id)
    return {"consented": True, "routedTo": body.pharmacyIds[0]}

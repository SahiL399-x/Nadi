from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_role
from app.models import User
from app.schemas.prescription import ConsentIn, PrescriptionOut
from app.services import audit_service, pharmacy_service, prescription_service

router = APIRouter(prefix="/v1/prescriptions", tags=["prescriptions"])


@router.get("/{prescription_id}", response_model=PrescriptionOut)
def get(prescription_id: str, user: User = Depends(get_current_user),
        db: Session = Depends(get_db)) -> PrescriptionOut:
    out = prescription_service.get_viewable(db, prescription_id, user)
    if out is None:
        raise HTTPException(status_code=404, detail="not found")
    audit_service.log(db, user.id, "view_prescription", "prescription", prescription_id)
    return out


@router.post("/{prescription_id}/consent")
def consent(prescription_id: str, body: ConsentIn, user: User = Depends(require_role("patient")),
            db: Session = Depends(get_db)) -> dict:
    if not body.pharmacyIds:
        raise HTTPException(status_code=400, detail="at least one pharmacy required")
    if not prescription_service.patient_owns(db, prescription_id, user.id):
        raise HTTPException(status_code=404, detail="not found")
    pharmacy_service.grant_consent(db, prescription_id, body.pharmacyIds)
    audit_service.log(db, user.id, "consent", "prescription", prescription_id)
    return {"consented": True, "routedTo": body.pharmacyIds[0]}

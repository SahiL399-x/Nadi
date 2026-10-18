from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models import (
    Consultation, OfferStatus, PharmacyOffer, Prescription, PrescriptionLine, User,
)
from app.services import audit_service, pharmacy_service

router = APIRouter(prefix="/v1/pharmacy", tags=["pharmacy"])


@router.get("/inbox")
def inbox(user: User = Depends(require_role("pharmacy")), db: Session = Depends(get_db)) -> list[dict]:
    offers = db.scalars(
        select(PharmacyOffer).where(PharmacyOffer.pharmacy_id == user.id)
        .where(PharmacyOffer.status == OfferStatus.PENDING)
    ).all()
    out = []
    for offer in offers:
        pres = db.get(Prescription, offer.prescription_id)
        consult = db.get(Consultation, pres.consultation_id)
        patient = db.get(User, consult.patient_id)
        lines = db.scalars(
            select(PrescriptionLine).where(PrescriptionLine.prescription_id == pres.id)
        ).all()
        out.append({
            "id": str(offer.id), "prescriptionId": str(pres.id),
            "patientName": patient.name if patient else "", "status": offer.status.value,
            "lines": [{"drug": ln.drug, "strength": ln.strength, "frequency": ln.frequency,
                       "durationDays": ln.duration_days} for ln in lines],
        })
    return out


@router.post("/offers/{offer_id}/accept")
def accept(offer_id: str, user: User = Depends(require_role("pharmacy")),
           db: Session = Depends(get_db)) -> dict:
    pharmacy_service.accept(db, offer_id)
    audit_service.log(db, user.id, "accept_offer", "offer", offer_id)
    return {"accepted": True}


@router.post("/offers/{offer_id}/decline")
def decline(offer_id: str, user: User = Depends(require_role("pharmacy")),
            db: Session = Depends(get_db)) -> dict:
    nxt = pharmacy_service.decline(db, offer_id)
    audit_service.log(db, user.id, "decline_offer", "offer", offer_id)
    return {"declined": True, "forwarded": nxt is not None}

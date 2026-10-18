import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models import TriageResult, User
from app.schemas.common import TriageInput, TriageResultOut
from app.schemas.consultation import BookIn, IntakeOut
from app.services import audit_service, consultation_service

router = APIRouter(prefix="/v1/consultations", tags=["consultations"])


def _triage_out(tr: TriageResult, labs: list | None = None) -> TriageResultOut:
    return TriageResultOut(
        acuity=tr.acuity.value if hasattr(tr.acuity, "value") else tr.acuity,
        acuityConfidence=tr.acuity_confidence,
        specialties=tr.specialties, drivers=tr.drivers,
        labs=labs or [], redFlags=tr.red_flags, modelVersion=tr.model_version,
    )


@router.post("/intake", response_model=IntakeOut)
def intake(body: TriageInput, user: User = Depends(require_role("patient")),
           db: Session = Depends(get_db)) -> IntakeOut:
    consult = consultation_service.intake(db, user.id, body)
    audit_service.log(db, user.id, "intake", "consultation", str(consult.id))
    return IntakeOut(consultationId=str(consult.id), jobId=str(uuid.uuid4()))


@router.get("/{consultation_id}/triage", response_model=TriageResultOut)
def get_triage(consultation_id: str, user: User = Depends(require_role("patient")),
               db: Session = Depends(get_db)) -> TriageResultOut:
    tr = consultation_service.get_triage(db, consultation_id)
    if tr is None:
        raise HTTPException(status_code=202, detail="pending")
    return _triage_out(tr)


@router.post("/{consultation_id}/book")
def book(consultation_id: str, body: BookIn, user: User = Depends(require_role("patient")),
         db: Session = Depends(get_db)) -> dict:
    consultation_service.book(db, consultation_id, body.doctorId, body.slot)
    audit_service.log(db, user.id, "book", "consultation", consultation_id)
    return {"booked": True}

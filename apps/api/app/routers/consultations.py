import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_role
from app.models import User
from app.schemas.common import TriageInput, TriageResultOut
from app.schemas.consultation import BookIn, ConsultationDetailOut, IntakeOut
from app.schemas.note import NoteIn, NoteOut
from app.services import audit_service, consultation_service, note_service

router = APIRouter(prefix="/v1/consultations", tags=["consultations"])


@router.post("/intake", response_model=IntakeOut)
def intake(
    body: TriageInput, user: User = Depends(require_role("patient")), db: Session = Depends(get_db)
) -> IntakeOut:
    consult = consultation_service.intake(db, user.id, body)
    audit_service.log(db, user.id, "intake", "consultation", str(consult.id))
    return IntakeOut(consultationId=str(consult.id), jobId=str(uuid.uuid4()))


@router.get("/{consultation_id}/triage")
def get_triage(
    consultation_id: str,
    user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
):
    consult = consultation_service.get_owned(db, consultation_id, user.id)
    if consult is None:
        raise HTTPException(status_code=404, detail="not found")
    tr = consultation_service.get_triage(db, consultation_id)
    if tr is None:
        # §9 contract: TriageResult | { status: 'pending' }
        return {"status": "pending"}
    return TriageResultOut.from_model(tr)


@router.post("/{consultation_id}/book")
def book(
    consultation_id: str,
    body: BookIn,
    user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
) -> dict:
    consult = consultation_service.get_owned(db, consultation_id, user.id)
    if consult is None:
        raise HTTPException(status_code=404, detail="not found")
    consultation_service.book(db, consult, body.doctorId, body.slot)
    audit_service.log(db, user.id, "book", "consultation", consultation_id)
    return {"booked": True}


@router.post("/{consultation_id}/notes")
def add_note(
    consultation_id: str,
    body: NoteIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not note_service.can_access(db, consultation_id, user):
        raise HTTPException(status_code=404, detail="not found")
    n = note_service.add(db, consultation_id, user.id, body.text)
    audit_service.log(db, user.id, "add_note", "consultation", consultation_id)
    return {"id": str(n.id)}


@router.get("/{consultation_id}/notes", response_model=list[NoteOut])
def list_notes(
    consultation_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if not note_service.can_access(db, consultation_id, user):
        raise HTTPException(status_code=404, detail="not found")
    return note_service.list_for(db, consultation_id, user.id)


@router.get("/{consultation_id}", response_model=ConsultationDetailOut)
def get_consultation(consultation_id: str, user: User = Depends(require_role("patient")),
                     db: Session = Depends(get_db)) -> ConsultationDetailOut:
    consult = consultation_service.get_owned(db, consultation_id, user.id)
    if consult is None:
        raise HTTPException(status_code=404, detail="not found")
    return ConsultationDetailOut(**consultation_service.detail(db, consult))

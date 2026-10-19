import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Consultation, ConsultationNote, User
from app.schemas.note import NoteOut


def can_access(db: Session, consultation_id, user: User) -> bool:
    c = db.get(Consultation, consultation_id)
    return c is not None and user.id in (c.patient_id, c.doctor_id)


def add(db: Session, consultation_id, author_id, text: str) -> ConsultationNote:
    note = ConsultationNote(
        id=uuid.uuid4(), consultation_id=consultation_id, author_id=author_id, text=text
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def list_for(db: Session, consultation_id) -> list[NoteOut]:
    rows = db.scalars(
        select(ConsultationNote)
        .where(ConsultationNote.consultation_id == consultation_id)
        .order_by(ConsultationNote.created_at.asc())
    ).all()
    return [NoteOut(id=str(n.id), text=n.text, createdAt=str(n.created_at)) for n in rows]

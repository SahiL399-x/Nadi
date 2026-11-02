import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ConsultationNote, User
from app.schemas.note import NoteOut
from app.services import consultation_service


def can_access(db: Session, consultation_id, user: User) -> bool:
    # A note is visible to the consultation's participants — the same rule as any
    # other per-consultation resource (see consultation_service.is_participant).
    return consultation_service.is_participant(db, consultation_id, user)


def add(db: Session, consultation_id, author_id, text: str) -> ConsultationNote:
    note = ConsultationNote(
        id=uuid.uuid4(), consultation_id=consultation_id, author_id=author_id, text=text
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def list_for(db: Session, consultation_id, author_id) -> list[NoteOut]:
    # Notes are a private notebook per participant: each side (patient, doctor)
    # sees only their own notes, never the other party's.
    rows = db.scalars(
        select(ConsultationNote)
        .where(ConsultationNote.consultation_id == consultation_id)
        .where(ConsultationNote.author_id == author_id)
        .order_by(ConsultationNote.created_at.asc())
    ).all()
    return [NoteOut(id=str(n.id), text=n.text, createdAt=str(n.created_at)) for n in rows]

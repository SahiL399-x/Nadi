from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Medicine
from app.schemas.medicine import MedicineOut


def search(db: Session, q: str | None, limit: int = 30) -> list[MedicineOut]:
    stmt = select(Medicine)
    if q:
        stmt = stmt.where(Medicine.name.ilike(f"%{q}%"))
    else:
        stmt = stmt.where(Medicine.is_common.is_(True))
    rows = db.scalars(stmt.order_by(Medicine.name.asc()).limit(limit)).all()
    return [MedicineOut(id=str(m.id), name=m.name, strength=m.strength, form=m.form) for m in rows]

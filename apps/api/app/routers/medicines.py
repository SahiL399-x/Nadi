from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models import User
from app.schemas.medicine import MedicineOut
from app.services import medicine_service

router = APIRouter(prefix="/v1/medicines", tags=["medicines"])


@router.get("", response_model=list[MedicineOut])
def search(
    q: str | None = None, _: User = Depends(require_role("doctor")), db: Session = Depends(get_db)
) -> list[MedicineOut]:
    return medicine_service.search(db, q)

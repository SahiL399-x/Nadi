from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models import User
from app.schemas.order import OrderOut
from app.schemas.pharmacy import OfferOut
from app.services import audit_service, pharmacy_service

router = APIRouter(prefix="/v1/pharmacy", tags=["pharmacy"])


class _StatusIn(BaseModel):
    status: str


@router.get("/inbox", response_model=list[OfferOut])
def inbox(user: User = Depends(require_role("pharmacy")), db: Session = Depends(get_db)):
    return pharmacy_service.inbox(db, user.id)


@router.get("/orders", response_model=list[OrderOut])
def orders(
    status: str | None = None,
    user: User = Depends(require_role("pharmacy")),
    db: Session = Depends(get_db),
):
    return pharmacy_service.orders(db, user.id, status)


@router.post("/offers/{offer_id}/accept")
def accept(
    offer_id: str, user: User = Depends(require_role("pharmacy")), db: Session = Depends(get_db)
) -> dict:
    if not pharmacy_service.accept(db, offer_id, user.id):
        raise HTTPException(status_code=404, detail="not found")
    audit_service.log(db, user.id, "accept_offer", "offer", offer_id)
    return {"accepted": True}


@router.post("/offers/{offer_id}/decline")
def decline(
    offer_id: str, user: User = Depends(require_role("pharmacy")), db: Session = Depends(get_db)
) -> dict:
    found, forwarded = pharmacy_service.decline(db, offer_id, user.id)
    if not found:
        raise HTTPException(status_code=404, detail="not found")
    audit_service.log(db, user.id, "decline_offer", "offer", offer_id)
    return {"declined": True, "forwarded": forwarded}


@router.post("/orders/{offer_id}/status")
def set_order_status(
    offer_id: str,
    body: _StatusIn,
    user: User = Depends(require_role("pharmacy")),
    db: Session = Depends(get_db),
) -> dict:
    found, allowed = pharmacy_service.set_status(db, offer_id, user.id, body.status)
    if not found:
        raise HTTPException(status_code=404, detail="not found")
    if not allowed:
        raise HTTPException(status_code=400, detail="illegal transition")
    return {"status": body.status.upper()}

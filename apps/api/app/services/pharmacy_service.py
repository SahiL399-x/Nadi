import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    OfferStatus, PharmacyConsent, PharmacyOffer, Prescription, PrescriptionStatus,
)


def grant_consent(db: Session, prescription_id, pharmacy_ids: list[str]) -> None:
    if not pharmacy_ids:
        raise ValueError("at least one pharmacy must be chosen")
    for rank, pid in enumerate(pharmacy_ids):
        db.add(PharmacyConsent(id=uuid.uuid4(), prescription_id=prescription_id,
                               pharmacy_id=pid, rank=rank))
    # open an offer for the first-ranked pharmacy only
    db.add(PharmacyOffer(id=uuid.uuid4(), prescription_id=prescription_id,
                         pharmacy_id=pharmacy_ids[0], status=OfferStatus.PENDING, rank=0))
    db.commit()


def _next_consent(db: Session, prescription_id, after_rank: int) -> PharmacyConsent | None:
    return db.scalar(
        select(PharmacyConsent).where(PharmacyConsent.prescription_id == prescription_id)
        .where(PharmacyConsent.rank > after_rank).order_by(PharmacyConsent.rank.asc())
    )


def decline(db: Session, offer_id) -> PharmacyOffer | None:
    offer = db.get(PharmacyOffer, offer_id)
    offer.status = OfferStatus.DECLINED
    nxt = _next_consent(db, offer.prescription_id, offer.rank)
    new_offer = None
    if nxt is not None:
        new_offer = PharmacyOffer(id=uuid.uuid4(), prescription_id=offer.prescription_id,
                                  pharmacy_id=nxt.pharmacy_id, status=OfferStatus.PENDING,
                                  rank=nxt.rank)
        db.add(new_offer)
    else:
        pres = db.get(Prescription, offer.prescription_id)
        pres.status = PrescriptionStatus.DECLINED
    db.commit()
    return new_offer


def accept(db: Session, offer_id) -> None:
    offer = db.get(PharmacyOffer, offer_id)
    offer.status = OfferStatus.ACCEPTED
    pres = db.get(Prescription, offer.prescription_id)
    pres.status = PrescriptionStatus.ACCEPTED
    db.commit()

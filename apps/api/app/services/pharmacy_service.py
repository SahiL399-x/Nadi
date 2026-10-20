import uuid

from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_MakePoint, ST_SetSRID
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Consultation,
    OfferStatus,
    Pharmacy,
    PharmacyConsent,
    PharmacyOffer,
    Prescription,
    PrescriptionLine,
    PrescriptionStatus,
    User,
)
from app.schemas.order import OrderOut
from app.schemas.pharmacy import OfferOut, PharmacyOut


def grant_consent(db: Session, prescription_id, pharmacy_ids: list[str]) -> None:
    for rank, pid in enumerate(pharmacy_ids):
        db.add(
            PharmacyConsent(
                id=uuid.uuid4(), prescription_id=prescription_id, pharmacy_id=pid, rank=rank
            )
        )
    # open an offer for the first-ranked pharmacy only
    db.add(
        PharmacyOffer(
            id=uuid.uuid4(),
            prescription_id=prescription_id,
            pharmacy_id=pharmacy_ids[0],
            status=OfferStatus.PENDING,
            rank=0,
        )
    )
    db.commit()


def inbox(db: Session, pharmacy_id) -> list[OfferOut]:
    rows = db.execute(
        select(PharmacyOffer, Prescription, User)
        .join(Prescription, Prescription.id == PharmacyOffer.prescription_id)
        .join(Consultation, Consultation.id == Prescription.consultation_id)
        .join(User, User.id == Consultation.patient_id)
        .where(PharmacyOffer.pharmacy_id == pharmacy_id)
        .where(PharmacyOffer.status == OfferStatus.PENDING)
    ).all()
    pres_ids = [pres.id for _, pres, _ in rows]
    lines_by_pres: dict = {}
    if pres_ids:
        for ln in db.scalars(
            select(PrescriptionLine).where(PrescriptionLine.prescription_id.in_(pres_ids))
        ):
            lines_by_pres.setdefault(ln.prescription_id, []).append(ln)
    return [
        OfferOut(
            id=str(offer.id),
            prescriptionId=str(pres.id),
            patientName=patient.name if patient else "",
            status=offer.status.value,
            lines=[
                {
                    "drug": ln.drug,
                    "strength": ln.strength,
                    "frequency": ln.frequency,
                    "durationDays": ln.duration_days,
                    "notes": ln.notes,
                }
                for ln in lines_by_pres.get(pres.id, [])
            ],
        )
        for offer, pres, patient in rows
    ]


def _point(lat: float, lng: float):
    return func.cast(ST_SetSRID(ST_MakePoint(lng, lat), 4326), type_=Pharmacy.location.type)


def search(db: Session, lat: float, lng: float, radius_km: float) -> list[PharmacyOut]:
    pt = _point(lat, lng)
    dist = ST_Distance(Pharmacy.location, pt)
    stmt = (
        select(Pharmacy, dist)
        .where(ST_DWithin(Pharmacy.location, pt, radius_km * 1000))
        .order_by(dist.asc())
    )
    rows = db.execute(stmt).all()
    out: list[PharmacyOut] = []
    for ph, d_m in rows:
        km = round(d_m / 1000.0, 1)
        out.append(
            PharmacyOut(
                id=str(ph.user_id),
                name=ph.name,
                distanceKm=km,
                deliversInMins=(0 if not ph.delivers else 15 + round(km * 3)),
                isOpen=ph.is_open,
            )
        )
    return out


def _next_consent(db: Session, prescription_id, after_rank: int) -> PharmacyConsent | None:
    return db.scalar(
        select(PharmacyConsent)
        .where(PharmacyConsent.prescription_id == prescription_id)
        .where(PharmacyConsent.rank > after_rank)
        .order_by(PharmacyConsent.rank.asc())
    )


def _owned_offer(db: Session, offer_id, pharmacy_id) -> PharmacyOffer | None:
    offer = db.get(PharmacyOffer, offer_id)
    if offer is None or offer.pharmacy_id != pharmacy_id:
        return None
    return offer


def decline(db: Session, offer_id, pharmacy_id) -> tuple[bool, bool]:
    """Returns (found, forwarded). found=False => unknown offer or not this pharmacy's."""
    offer = _owned_offer(db, offer_id, pharmacy_id)
    if offer is None:
        return (False, False)
    offer.status = OfferStatus.DECLINED
    nxt = _next_consent(db, offer.prescription_id, offer.rank)
    if nxt is not None:
        db.add(
            PharmacyOffer(
                id=uuid.uuid4(),
                prescription_id=offer.prescription_id,
                pharmacy_id=nxt.pharmacy_id,
                status=OfferStatus.PENDING,
                rank=nxt.rank,
            )
        )
    else:
        pres = db.get(Prescription, offer.prescription_id)
        pres.status = PrescriptionStatus.DECLINED
    db.commit()
    return (True, nxt is not None)


def accept(db: Session, offer_id, pharmacy_id) -> bool:
    """Returns False if the offer is unknown or not owned by this pharmacy."""
    offer = _owned_offer(db, offer_id, pharmacy_id)
    if offer is None:
        return False
    offer.status = OfferStatus.ACCEPTED
    pres = db.get(Prescription, offer.prescription_id)
    pres.status = PrescriptionStatus.ACCEPTED
    db.commit()
    return True


_ALLOWED: dict[str, set[str]] = {
    "PENDING": {"TO_VERIFY", "VERIFIED", "PREPARING", "CANCELLED"},
    "TO_VERIFY": {"VERIFIED", "PREPARING", "CANCELLED"},
    "VERIFIED": {"PREPARING", "CANCELLED"},
    "PREPARING": {"OUT_FOR_DELIVERY", "CANCELLED"},
    "OUT_FOR_DELIVERY": {"DELIVERED", "CANCELLED"},
    "DELIVERED": {"COMPLETED"},
    "COMPLETED": set(),
    "CANCELLED": set(),
    "DECLINED": set(),
    "ACCEPTED": {"PREPARING", "CANCELLED"},
}


def set_status(db: Session, offer_id, pharmacy_id, new_status: str) -> tuple[bool, bool]:
    """Returns (found, allowed)."""
    offer = _owned_offer(db, offer_id, pharmacy_id)
    if offer is None:
        return (False, False)
    target = new_status.upper()
    if target not in _ALLOWED.get(offer.status.value, set()):
        return (True, False)
    offer.status = OfferStatus(target)
    if target in ("DELIVERED", "COMPLETED"):
        pres = db.get(Prescription, offer.prescription_id)
        if pres is not None:
            pres.status = PrescriptionStatus.DELIVERED
    db.commit()
    return (True, True)


def _demo_total(lines: list) -> int:
    # Deterministic demo figure — no pricing engine exists. Stable per line set.
    return sum(40 + 10 * ln.duration_days for ln in lines)


def orders(db: Session, pharmacy_id, status: str | None) -> list[OrderOut]:
    stmt = (
        select(PharmacyOffer, Prescription, User)
        .join(Prescription, Prescription.id == PharmacyOffer.prescription_id)
        .join(Consultation, Consultation.id == Prescription.consultation_id)
        .join(User, User.id == Consultation.patient_id)
        .where(PharmacyOffer.pharmacy_id == pharmacy_id)
    )
    if status and status != "all":
        try:
            offer_status = OfferStatus(status.upper())
        except ValueError:
            return []
        stmt = stmt.where(PharmacyOffer.status == offer_status)
    rows = db.execute(stmt).all()
    pres_ids = [pres.id for _, pres, _ in rows]
    lines_by_pres: dict = {}
    if pres_ids:
        for ln in db.scalars(
            select(PrescriptionLine).where(PrescriptionLine.prescription_id.in_(pres_ids))
        ):
            lines_by_pres.setdefault(ln.prescription_id, []).append(ln)
    out: list[OrderOut] = []
    for offer, pres, patient in rows:
        lines = lines_by_pres.get(pres.id, [])
        out.append(
            OrderOut(
                id=str(offer.id),
                orderNo=offer.order_no or f"NP{str(offer.id)[:4].upper()}",
                patientName=patient.name if patient else "",
                phone=patient.phone if patient else "",
                itemsCount=len(lines),
                totalInr=_demo_total(lines),
                status=offer.status.value,
                placedAt=str(pres.issued_at),
            )
        )
    return out

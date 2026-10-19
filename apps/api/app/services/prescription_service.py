import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Consultation,
    PharmacyConsent,
    Prescription,
    PrescriptionLine,
    Referral,
    User,
)
from app.schemas.doctor_lists import DoctorPrescriptionOut
from app.schemas.prescription import PrescriptionLineIn, PrescriptionLineOut, PrescriptionOut


def create(db: Session, consultation_id, lines: list[PrescriptionLineIn]) -> Prescription:
    pres = Prescription(id=uuid.uuid4(), consultation_id=consultation_id)
    db.add(pres)
    db.flush()
    for ln in lines:
        db.add(
            PrescriptionLine(
                id=uuid.uuid4(),
                prescription_id=pres.id,
                drug=ln.drug,
                strength=ln.strength,
                frequency=ln.frequency,
                duration_days=ln.durationDays,
                notes=ln.notes,
            )
        )
    db.commit()
    db.refresh(pres)
    return pres


def refer(db: Session, consultation_id, from_doctor_id, to_specialty: str, reason: str) -> Referral:
    ref = Referral(
        id=uuid.uuid4(),
        consultation_id=consultation_id,
        from_doctor_id=from_doctor_id,
        to_specialty=to_specialty,
        reason=reason,
    )
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return ref


def _can_view(db: Session, user: User, consult: Consultation, pres: Prescription) -> bool:
    # The owning patient and the prescribing doctor may always view it.
    if user.id in (consult.patient_id, consult.doctor_id):
        return True
    # A pharmacy may view it only if the patient consented to route it there.
    consent = db.scalar(
        select(PharmacyConsent)
        .where(PharmacyConsent.prescription_id == pres.id)
        .where(PharmacyConsent.pharmacy_id == user.id)
    )
    return consent is not None


def get_viewable(db: Session, prescription_id, user: User) -> PrescriptionOut | None:
    """Return the prescription if `user` is authorized to see it, else None.

    None covers both "not found" and "not authorized" so existence is not leaked.
    """
    pres = db.get(Prescription, prescription_id)
    if pres is None:
        return None
    consult = db.get(Consultation, pres.consultation_id)
    if consult is None or not _can_view(db, user, consult, pres):
        return None
    lines = db.scalars(
        select(PrescriptionLine).where(PrescriptionLine.prescription_id == pres.id)
    ).all()
    patient = db.get(User, consult.patient_id)
    doctor = db.get(User, consult.doctor_id) if consult.doctor_id else None
    return PrescriptionOut(
        id=str(pres.id),
        patientName=patient.name if patient else "",
        doctorName=doctor.name if doctor else "",
        issuedAt=str(pres.issued_at),
        lines=[
            PrescriptionLineOut(
                drug=ln.drug,
                strength=ln.strength,
                frequency=ln.frequency,
                durationDays=ln.duration_days,
                notes=ln.notes,
            )
            for ln in lines
        ],
        status=pres.status.value,
    )


def list_for_doctor(db: Session, doctor_id, status: str | None):
    rows = db.execute(
        select(Prescription, User)
        .join(Consultation, Consultation.id == Prescription.consultation_id)
        .join(User, User.id == Consultation.patient_id)
        .where(Consultation.doctor_id == doctor_id)
    ).all()
    out = []
    for pres, patient in rows:
        s = pres.status.value
        if status == "active" and s not in ("PENDING", "ACCEPTED"):
            continue
        if status == "completed" and s not in ("DELIVERED",):
            continue
        first = (
            db.scalar(
                select(PrescriptionLine.drug)
                .where(PrescriptionLine.prescription_id == pres.id)
                .limit(1)
            )
            or ""
        )
        out.append(
            DoctorPrescriptionOut(
                id=str(pres.id),
                patientName=patient.name,
                issuedAt=str(pres.issued_at),
                firstDrug=first,
                status=s,
            )
        )
    return out


def patient_owns(db: Session, prescription_id, patient_id) -> bool:
    """True if the prescription's consultation belongs to the given patient."""
    pres = db.get(Prescription, prescription_id)
    if pres is None:
        return False
    consult = db.get(Consultation, pres.consultation_id)
    return consult is not None and consult.patient_id == patient_id

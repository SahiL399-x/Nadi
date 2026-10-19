from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Consultation,
    Patient,
    PatientCondition,
    PatientVisit,
    Prescription,
    PrescriptionLine,
    User,
)
from app.schemas.patient_profile import PatientProfileOut, VisitOut


def owned_by_doctor(db: Session, patient_id, doctor_id) -> bool:
    return (
        db.scalar(
            select(Consultation.id)
            .where(Consultation.patient_id == patient_id)
            .where(Consultation.doctor_id == doctor_id)
            .limit(1)
        )
        is not None
    )


def profile(db: Session, patient_id) -> PatientProfileOut | None:
    user = db.get(User, patient_id)
    if user is None:
        return None
    patient = db.get(Patient, patient_id)
    conds = list(
        db.scalars(select(PatientCondition).where(PatientCondition.patient_id == patient_id))
    )
    conditions = [c.label for c in conds if c.kind == "condition"]
    allergies = [c.label for c in conds if c.kind == "allergy"]
    family = [c.label for c in conds if c.kind == "family_history"]
    visits = [
        VisitOut(visitedAt=v.visited_at, summary=v.summary, status=v.status)
        for v in db.scalars(
            select(PatientVisit)
            .where(PatientVisit.patient_id == patient_id)
            .order_by(PatientVisit.visited_at.desc())
        )
    ]
    pres_lines = db.scalars(
        select(PrescriptionLine)
        .join(Prescription, Prescription.id == PrescriptionLine.prescription_id)
        .join(Consultation, Consultation.id == Prescription.consultation_id)
        .where(Consultation.patient_id == patient_id)
    )
    prescriptions = [f"{ln.drug} {ln.strength}" for ln in pres_lines]
    return PatientProfileOut(
        name=user.name,
        age=(patient.age if patient and patient.age else 0),
        sex=(patient.sex if patient and patient.sex else "O"),
        conditions=conditions,
        allergies=allergies,
        familyHistory=family,
        noKnownAllergies=(len(allergies) == 0),
        latestVisit=visits[0] if visits else None,
        visits=visits,
        prescriptions=prescriptions,
    )

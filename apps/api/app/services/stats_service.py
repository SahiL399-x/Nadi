from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Consultation, ConsultationStatus, Prescription, User
from app.schemas.stats import DoctorStatsOut

_PENDING = (ConsultationStatus.BOOKED, ConsultationStatus.ARRIVED, ConsultationStatus.IN_PROGRESS)


def doctor_stats(db: Session, doctor_id) -> DoctorStatsOut:
    appts = list(db.scalars(select(Consultation).where(Consultation.doctor_id == doctor_id)))
    appointments_today = len(appts)  # seed puts the demo day on these; fine for the demo scope
    pending = sum(1 for c in appts if c.status in _PENDING)
    completed = sum(1 for c in appts if c.status == ConsultationStatus.DONE)
    prescriptions_issued = (
        db.scalar(
            select(func.count(Prescription.id))
            .join(Consultation, Consultation.id == Prescription.consultation_id)
            .where(Consultation.doctor_id == doctor_id)
        )
        or 0
    )
    week_ago = datetime.now(UTC) - timedelta(days=7)
    new_patients = (
        db.scalar(
            select(func.count(func.distinct(Consultation.patient_id)))
            .join(User, User.id == Consultation.patient_id)
            .where(Consultation.doctor_id == doctor_id)
            .where(User.created_at >= week_ago)
        )
        or 0
    )
    return DoctorStatsOut(
        appointmentsToday=appointments_today,
        pending=pending,
        completed=completed,
        prescriptionsIssued=prescriptions_issued,
        newPatients=new_patients,
    )

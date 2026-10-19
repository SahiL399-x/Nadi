from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Consultation, Report, User
from app.schemas.doctor_lists import LabReportOut


def list_for_doctor(db: Session, doctor_id, status: str | None) -> list[LabReportOut]:
    rows = db.execute(
        select(Report, Consultation, User)
        .join(Consultation, Consultation.id == Report.consultation_id)
        .join(User, User.id == Consultation.patient_id)
        .where(Consultation.doctor_id == doctor_id)
    ).all()
    out = []
    for report, consult, patient in rows:
        label = "Completed" if report.ocr_status == "done" else "Pending"
        if status == "pending" and label != "Pending":
            continue
        if status == "completed" and label != "Completed":
            continue
        out.append(
            LabReportOut(
                id=str(report.id),
                patientName=patient.name,
                date=str(consult.created_at),
                status=label,
            )
        )
    return out

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models import Consultation, Doctor, Prescription, PrescriptionLine, Report, User
from app.schemas.me import MyAppointmentOut, MyPrescriptionOut, MyReportOut

router = APIRouter(prefix="/v1/me", tags=["me"])


@router.get("/appointments", response_model=list[MyAppointmentOut])
def appointments(
    user: User = Depends(require_role("patient")), db: Session = Depends(get_db)
) -> list[MyAppointmentOut]:
    rows = db.execute(
        select(Consultation, User.name, Doctor.specialty)
        .join(User, User.id == Consultation.doctor_id)
        .join(Doctor, Doctor.user_id == Consultation.doctor_id)
        .where(Consultation.patient_id == user.id)
        .order_by(Consultation.created_at.desc())
    ).all()
    return [
        MyAppointmentOut(
            consultationId=str(c.id), doctorName=name, specialty=spec,
            status=c.status.value, slot=c.booked_for or "",
        )
        for c, name, spec in rows
    ]


@router.get("/prescriptions", response_model=list[MyPrescriptionOut])
def prescriptions(
    user: User = Depends(require_role("patient")), db: Session = Depends(get_db)
) -> list[MyPrescriptionOut]:
    rows = db.execute(
        select(Prescription, User.name, func.count(PrescriptionLine.id))
        .join(Consultation, Consultation.id == Prescription.consultation_id)
        .join(User, User.id == Consultation.doctor_id)
        .join(PrescriptionLine, PrescriptionLine.prescription_id == Prescription.id, isouter=True)
        .where(Consultation.patient_id == user.id)
        .group_by(Prescription.id, User.name)
        .order_by(Prescription.issued_at.desc())
    ).all()
    return [
        MyPrescriptionOut(id=str(p.id), doctorName=name, status=p.status.value, items=int(items))
        for p, name, items in rows
    ]


@router.get("/reports", response_model=list[MyReportOut])
def reports(
    user: User = Depends(require_role("patient")), db: Session = Depends(get_db)
) -> list[MyReportOut]:
    rows = db.execute(
        select(Report)
        .join(Consultation, Consultation.id == Report.consultation_id)
        .where(Consultation.patient_id == user.id)
    ).scalars().all()
    return [MyReportOut(id=str(r.id), objectKey=r.object_key) for r in rows]

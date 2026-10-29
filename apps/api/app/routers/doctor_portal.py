from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models import User
from app.schemas.appointment import AppointmentOut
from app.schemas.availability import AvailabilityIn, AvailabilityOut
from app.schemas.consultation import QueueItemOut
from app.schemas.doctor_lists import DoctorPrescriptionOut, LabReportOut
from app.schemas.doctor_profile import DoctorProfileIn, DoctorProfileOut
from app.schemas.patient_profile import PatientProfileOut
from app.schemas.prescription import PrescribeIn, ReferIn
from app.schemas.report_view import ReportViewOut
from app.schemas.stats import DoctorStatsOut
from app.services import (
    audit_service,
    availability_service,
    consultation_service,
    doctor_service,
    lab_report_service,
    patient_service,
    prescription_service,
    report_view_service,
    stats_service,
)

router = APIRouter(prefix="/v1/doctor", tags=["doctor"])


@router.get("/stats", response_model=DoctorStatsOut)
def stats(user: User = Depends(require_role("doctor")), db: Session = Depends(get_db)):
    return stats_service.doctor_stats(db, user.id)


@router.get("/queue", response_model=list[QueueItemOut])
def queue(user: User = Depends(require_role("doctor")), db: Session = Depends(get_db)):
    items = consultation_service.doctor_queue(db, user.id)
    audit_service.log(db, user.id, "view_queue", "doctor", str(user.id))
    return items


@router.get("/appointments", response_model=list[AppointmentOut])
def appointments(
    date: date | None = None,
    user: User = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
):
    return consultation_service.doctor_appointments(db, user.id, date)


@router.get("/patients/{patient_id}", response_model=PatientProfileOut)
def patient_profile(
    patient_id: str,
    user: User = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
):
    if not patient_service.owned_by_doctor(db, patient_id, user.id):
        raise HTTPException(status_code=404, detail="not found")
    out = patient_service.profile(db, patient_id)
    if out is None:
        raise HTTPException(status_code=404, detail="not found")
    return out


@router.get("/patients/{patient_id}/reports", response_model=list[ReportViewOut])
def patient_reports(
    patient_id: str,
    user: User = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
):
    if not patient_service.owned_by_doctor(db, patient_id, user.id):
        raise HTTPException(status_code=404, detail="not found")
    return report_view_service.list_for_patient(db, user.id, patient_id)


@router.get("/prescriptions", response_model=list[DoctorPrescriptionOut])
def doctor_prescriptions(
    status: str | None = None,
    user: User = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
):
    return prescription_service.list_for_doctor(db, user.id, status)


@router.get("/lab-reports", response_model=list[LabReportOut])
def doctor_lab_reports(
    status: str | None = None,
    user: User = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
):
    return lab_report_service.list_for_doctor(db, user.id, status)


@router.get("/availability", response_model=list[AvailabilityOut])
def get_availability(user: User = Depends(require_role("doctor")), db: Session = Depends(get_db)):
    return availability_service.get(db, user.id)


@router.put("/availability", response_model=list[AvailabilityOut])
def put_availability(
    body: AvailabilityIn,
    user: User = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
):
    return availability_service.put(db, user.id, body.days)


@router.get("/profile", response_model=DoctorProfileOut)
def get_profile(user: User = Depends(require_role("doctor")), db: Session = Depends(get_db)):
    out = doctor_service.profile(db, user.id)
    if out is None:
        raise HTTPException(status_code=404, detail="not found")
    return out


@router.put("/profile", response_model=DoctorProfileOut)
def put_profile(
    body: DoctorProfileIn,
    user: User = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
):
    out = doctor_service.update_profile(db, user.id, body.clinicAddress, body.about)
    if out is None:
        raise HTTPException(status_code=404, detail="not found")
    return out


@router.post("/consultations/{consultation_id}/refer")
def refer(
    consultation_id: str,
    body: ReferIn,
    user: User = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
) -> dict:
    if consultation_service.get_for_doctor(db, consultation_id, user.id) is None:
        raise HTTPException(status_code=404, detail="not found")
    prescription_service.refer(db, consultation_id, user.id, body.toSpecialty, body.reason)
    audit_service.log(db, user.id, "refer", "consultation", consultation_id)
    return {"referred": True}


@router.post("/consultations/{consultation_id}/prescribe")
def prescribe(
    consultation_id: str,
    body: PrescribeIn,
    user: User = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
) -> dict:
    if consultation_service.get_for_doctor(db, consultation_id, user.id) is None:
        raise HTTPException(status_code=404, detail="not found")
    pres = prescription_service.create(db, consultation_id, body.lines)
    audit_service.log(db, user.id, "prescribe", "consultation", consultation_id)
    return {"prescriptionId": str(pres.id)}

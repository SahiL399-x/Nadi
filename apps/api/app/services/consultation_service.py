import json
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Consultation, ConsultationStatus, Patient, Prescription, Report, TriageResult, User
from app.schemas.appointment import AppointmentOut, status_label
from app.schemas.common import TriageInput, TriageResultOut
from app.schemas.consultation import QueueItemOut
from app.services import ml_client

_ACUITY_ORDER = {"EMERGENCY": 0, "URGENT": 1, "PRIORITY": 2, "ROUTINE": 3}


def intake(db: Session, patient_id, inp: TriageInput) -> Consultation:
    # Ensure the patient profile exists and carries the age/sex given at intake,
    # so the doctor queue (which joins `patients`) resolves and shows real values.
    patient = db.get(Patient, patient_id)
    if patient is None:
        patient = Patient(user_id=patient_id)
        db.add(patient)
    if inp.age is not None:
        patient.age = inp.age
    if inp.sex is not None:
        patient.sex = inp.sex

    consult = Consultation(
        id=uuid.uuid4(),
        patient_id=patient_id,
        status=ConsultationStatus.PENDING,
        symptom_text_raw=inp.symptomText,
    )
    db.add(consult)
    db.flush()

    labs: list[dict] = []
    for object_key in inp.reportImageUris:
        # Use the key the client actually uploaded to (from /v1/uploads/sign)
        # rather than fabricating one, so the real report drives extraction.
        result = ml_client.document(object_key)
        db.add(
            Report(
                id=uuid.uuid4(),
                consultation_id=consult.id,
                object_key=object_key,
                ocr_status="done",
                extraction_json=json.dumps(result),
            )
        )
        labs.extend(result.get("labs", []))

    try:
        result = ml_client.triage(
            {
                "symptomText": inp.symptomText,
                "labs": labs,
                "age": inp.age,
                "sex": inp.sex,
                "lang": inp.lang,
            }
        )
    except Exception:
        # Don't leave a half-built transaction open across a failed network call.
        db.rollback()
        raise
    db.add(
        TriageResult(
            id=uuid.uuid4(),
            consultation_id=consult.id,
            acuity=result["acuity"],
            acuity_confidence=result["acuityConfidence"],
            specialties=result["specialties"],
            drivers=result["drivers"],
            labs=result.get("labs", []),
            red_flags=result["redFlags"],
            model_version=result["modelVersion"],
        )
    )
    consult.status = ConsultationStatus.TRIAGED
    consult.symptom_text_normalised = inp.symptomText
    db.commit()
    db.refresh(consult)
    return consult


def get_owned(db: Session, consultation_id, patient_id) -> Consultation | None:
    """Fetch a consultation only if it belongs to the given patient."""
    consult = db.get(Consultation, consultation_id)
    if consult is None or consult.patient_id != patient_id:
        return None
    return consult


def get_triage(db: Session, consultation_id) -> TriageResult | None:
    return db.scalar(select(TriageResult).where(TriageResult.consultation_id == consultation_id))


def detail(db: Session, consult: Consultation) -> dict:
    pres = db.scalar(select(Prescription).where(Prescription.consultation_id == consult.id))
    return {
        "id": str(consult.id), "status": consult.status.value,
        "doctorId": str(consult.doctor_id) if consult.doctor_id else None,
        "bookedFor": consult.booked_for,
        "prescriptionId": str(pres.id) if pres else None,
    }


def book(db: Session, consult: Consultation, doctor_id, slot: str) -> Consultation:
    consult.doctor_id = doctor_id
    consult.booked_for = slot
    consult.status = ConsultationStatus.BOOKED
    db.commit()
    db.refresh(consult)
    return consult


def get_for_doctor(db: Session, consultation_id, doctor_id) -> Consultation | None:
    """Fetch a consultation only if it is assigned to the given doctor."""
    consult = db.get(Consultation, consultation_id)
    if consult is None or consult.doctor_id != doctor_id:
        return None
    return consult


def doctor_queue(db: Session, doctor_id) -> list[QueueItemOut]:
    rows = db.execute(
        select(Consultation, TriageResult, User, Patient)
        .join(TriageResult, TriageResult.consultation_id == Consultation.id)
        .join(User, User.id == Consultation.patient_id)
        .outerjoin(Patient, Patient.user_id == Consultation.patient_id)
        .where(Consultation.doctor_id == doctor_id)
        .where(Consultation.status == ConsultationStatus.BOOKED)
    ).all()
    items = [
        QueueItemOut(
            id=str(consult.id),
            patientId=str(consult.patient_id),
            patientName=patient_user.name,
            patientAge=(patient.age if patient and patient.age is not None else 0),
            patientSex=(patient.sex if patient and patient.sex else "O"),
            acuity=tr.acuity.value,
            complaint=consult.symptom_text_raw,
            bookedFor=consult.booked_for or "",
            triage=TriageResultOut.from_model(tr),
        )
        for consult, tr, patient_user, patient in rows
    ]
    items.sort(key=lambda i: _ACUITY_ORDER[i.acuity])
    return items


def doctor_appointments(db: Session, doctor_id, on: date | None) -> list[AppointmentOut]:
    stmt = (
        select(Consultation, User, Patient, TriageResult)
        .join(User, User.id == Consultation.patient_id)
        .outerjoin(Patient, Patient.user_id == Consultation.patient_id)
        .outerjoin(TriageResult, TriageResult.consultation_id == Consultation.id)
        .where(Consultation.doctor_id == doctor_id)
        .where(
            Consultation.status.in_(
                [
                    ConsultationStatus.BOOKED,
                    ConsultationStatus.ARRIVED,
                    ConsultationStatus.IN_PROGRESS,
                    ConsultationStatus.DONE,
                ]
            )
        )
    )
    rows = db.execute(stmt).all()
    out = []
    for c, user, patient, tr in rows:
        when = c.scheduled_at
        if on is not None and (when is None or when.date() != on):
            continue
        out.append(
            AppointmentOut(
                id=str(c.id),
                patientId=str(c.patient_id),
                patientName=user.name,
                patientAge=(patient.age if patient and patient.age is not None else 0),
                patientSex=(patient.sex if patient and patient.sex else "O"),
                photoUrl="",
                time=(when.strftime("%H:%M") if when else (c.booked_for or "")),
                status=status_label(c.status.value),
                acuity=(tr.acuity.value if tr else None),
                complaint=c.symptom_text_raw,
            )
        )
    out.sort(key=lambda a: a.time)
    return out

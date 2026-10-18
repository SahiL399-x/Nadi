import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Consultation, ConsultationStatus, Report, TriageResult
from app.schemas.common import TriageInput
from app.services import ml_client


def intake(db: Session, patient_id, inp: TriageInput) -> Consultation:
    consult = Consultation(
        id=uuid.uuid4(), patient_id=patient_id,
        status=ConsultationStatus.PENDING, symptom_text_raw=inp.symptomText,
    )
    db.add(consult)
    db.flush()

    labs: list[dict] = []
    for i, uri in enumerate(inp.reportImageUris):
        key = f"consult/{consult.id}/report{i}"
        db.add(Report(id=uuid.uuid4(), consultation_id=consult.id, object_key=key, ocr_status="done"))
        labs.extend(ml_client.document(key))

    result = ml_client.triage(
        {"symptomText": inp.symptomText, "labs": labs, "age": inp.age, "sex": inp.sex, "lang": inp.lang}
    )
    db.add(
        TriageResult(
            id=uuid.uuid4(), consultation_id=consult.id,
            acuity=result["acuity"], acuity_confidence=result["acuityConfidence"],
            specialties=result["specialties"], drivers=result["drivers"],
            red_flags=result["redFlags"], model_version=result["modelVersion"],
        )
    )
    consult.status = ConsultationStatus.TRIAGED
    consult.symptom_text_normalised = inp.symptomText
    db.commit()
    db.refresh(consult)
    return consult


def get_triage(db: Session, consultation_id) -> TriageResult | None:
    return db.scalar(
        select(TriageResult).where(TriageResult.consultation_id == consultation_id)
    )


def book(db: Session, consultation_id, doctor_id, slot: str) -> Consultation:
    consult = db.get(Consultation, consultation_id)
    consult.doctor_id = doctor_id
    consult.booked_for = slot
    consult.status = ConsultationStatus.BOOKED
    db.commit()
    db.refresh(consult)
    return consult

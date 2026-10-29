import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Consultation, Report
from app.schemas.report_view import ReportViewOut
from app.services import storage_service


def _parse(extraction_json: str | None) -> tuple[bool, list[dict], bool]:
    """(extracted, fields, needsReview). Null/malformed -> (False, [], False)."""
    if not extraction_json:
        return False, [], False
    try:
        data = json.loads(extraction_json)
    except (ValueError, TypeError):
        return False, [], False
    return True, list(data.get("fields", [])), bool(data.get("needsReview", False))


def list_for_patient(db: Session, doctor_id, patient_id) -> list[ReportViewOut]:
    rows = db.execute(
        select(Report, Consultation)
        .join(Consultation, Consultation.id == Report.consultation_id)
        .where(Consultation.patient_id == patient_id)
        .where(Consultation.doctor_id == doctor_id)
        .order_by(Consultation.created_at)
    ).all()
    out: list[ReportViewOut] = []
    for report, consult in rows:
        extracted, fields, needs_review = _parse(report.extraction_json)
        out.append(
            ReportViewOut(
                reportId=str(report.id),
                kind="pdf" if report.object_key.endswith(".pdf") else "image",
                imageUrl=storage_service.presign_get(report.object_key),
                date=consult.created_at.strftime("%d %b %Y") if consult.created_at else "",
                needsReview=needs_review,
                extracted=extracted,
                fields=fields,
            )
        )
    return out

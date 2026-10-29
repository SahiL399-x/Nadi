import json
import uuid

from app.models import Consultation, ConsultationStatus, Patient, Report, Role, User
import app.services.storage_service as storage_service


def _doctor_token(client, db):
    phone = f"+91{uuid.uuid4().int % 10**10:010d}"
    db.add(User(id=uuid.uuid4(), phone=phone, role=Role.doctor, name="Dr R"))
    db.commit()
    client.post("/v1/auth/request-otp", json={"phone": phone})
    r = client.post("/v1/auth/verify-otp", json={"phone": phone, "code": "123456"})
    return r.json()["accessToken"], r.json()["userId"]


def _patient_with_report(db, doctor_id, object_key, extraction_json):
    pid = uuid.uuid4()
    db.add(User(id=pid, phone=f"+91{uuid.uuid4().int % 10**10:010d}", role=Role.patient, name="P"))
    db.flush()
    db.add(Patient(user_id=pid, age=30, sex="F"))
    cid = uuid.uuid4()
    db.add(Consultation(id=cid, patient_id=pid, doctor_id=doctor_id,
                        status=ConsultationStatus.BOOKED, symptom_text_raw="x"))
    db.flush()
    db.add(Report(id=uuid.uuid4(), consultation_id=cid, object_key=object_key,
                  ocr_status="done", extraction_json=extraction_json))
    db.commit()
    return str(pid)


def test_reports_returns_extraction_for_owned_patient(client, db, monkeypatch):
    monkeypatch.setattr(storage_service, "presign_get", lambda key: f"http://minio/{key}?sig=x")
    token, doctor_id = _doctor_token(client, db)
    extraction = json.dumps({"fields": [{"testNameNormalized": "Haemoglobin", "flag": "L"}],
                             "needsReview": True})
    pid = _patient_with_report(db, doctor_id, "reports/upload/u/a.webp", extraction)
    r = client.get(f"/v1/doctor/patients/{pid}/reports", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["kind"] == "image"
    assert body[0]["imageUrl"].startswith("http")
    assert body[0]["extracted"] is True
    assert body[0]["needsReview"] is True
    assert body[0]["fields"][0]["testNameNormalized"] == "Haemoglobin"


def test_reports_404_for_unowned_patient(client, db, monkeypatch):
    monkeypatch.setattr(storage_service, "presign_get", lambda key: "x")
    token, _ = _doctor_token(client, db)
    other_doctor = uuid.uuid4()
    db.add(User(id=other_doctor, phone=f"+91{uuid.uuid4().int % 10**10:010d}", role=Role.doctor, name="Other"))
    db.commit()
    pid = _patient_with_report(db, other_doctor, "reports/upload/u/b.webp", "{}")
    r = client.get(f"/v1/doctor/patients/{pid}/reports", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


def test_reports_pdf_kind_and_null_extraction(client, db, monkeypatch):
    monkeypatch.setattr(storage_service, "presign_get", lambda key: f"http://minio/{key}")
    token, doctor_id = _doctor_token(client, db)
    pid = _patient_with_report(db, doctor_id, "reports/upload/u/c.pdf", None)
    r = client.get(f"/v1/doctor/patients/{pid}/reports", headers={"Authorization": f"Bearer {token}"})
    body = r.json()
    assert body[0]["kind"] == "pdf"
    assert body[0]["extracted"] is False
    assert body[0]["fields"] == []


def test_reports_non_dict_json_extraction(client, db, monkeypatch):
    monkeypatch.setattr(storage_service, "presign_get", lambda key: f"http://minio/{key}")
    token, doctor_id = _doctor_token(client, db)
    pid = _patient_with_report(db, doctor_id, "reports/upload/u/d.webp", "[]")
    r = client.get(f"/v1/doctor/patients/{pid}/reports", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body[0]["extracted"] is False
    assert body[0]["fields"] == []

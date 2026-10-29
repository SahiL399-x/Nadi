import httpx
import json
import uuid
from sqlalchemy import select
from app.models import Report
from app.services import ml_client


def _stub_ml(monkeypatch):
    from app.services import ml_client

    def fake_triage(payload):
        return {
            "acuity": "EMERGENCY" if "chest" in payload["symptomText"] else "ROUTINE",
            "acuityConfidence": 0.9,
            "specialties": [{"name": "Emergency Medicine", "score": 0.8},
                            {"name": "Cardiology", "score": 0.1},
                            {"name": "General Medicine", "score": 0.1}],
            "drivers": [{"feature": "f", "contribution": 1.0}],
            "labs": payload["labs"],
            "redFlags": ["chest pain with breathlessness"] if "chest" in payload["symptomText"] else [],
            "modelVersion": "stub-keyword-v0",
        }

    monkeypatch.setattr(ml_client, "triage", fake_triage)
    monkeypatch.setattr(ml_client, "document", lambda k: [])


def test_intake_then_triage_emergency(client, patient_token, monkeypatch):
    _stub_ml(monkeypatch)
    h = {"Authorization": f"Bearer {patient_token}"}
    r = client.post("/v1/consultations/intake",
                    json={"symptomText": "chest pain and breath", "reportImageUris": [],
                          "age": 50, "sex": "M", "lang": "en"}, headers=h)
    assert r.status_code == 200
    cid = r.json()["consultationId"]
    t = client.get(f"/v1/consultations/{cid}/triage", headers=h)
    assert t.status_code == 200
    assert t.json()["acuity"] == "EMERGENCY"
    assert t.json()["redFlags"]
    assert t.json()["modelVersion"] == "stub-keyword-v0"


def test_get_consultation_returns_detail_with_prescription_id(client, patient_token):
    h = {"Authorization": f"Bearer {patient_token}"}
    intake = client.post("/v1/consultations/intake",
        json={"symptomText": "fever and cough", "reportImageUris": [], "lang": "en"}, headers=h)
    cid = intake.json()["consultationId"]
    r = client.get(f"/v1/consultations/{cid}", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == cid
    assert body["status"] in ("TRIAGED", "BOOKED", "PENDING")
    assert "prescriptionId" in body


def test_intake_persists_extraction_json(client, patient_token, db, monkeypatch):
    monkeypatch.setattr(
        ml_client, "document",
        lambda key: {"labs": [{"analyte": "Haemoglobin", "value": 9.1, "unit": "g/dL",
                                "refRange": "12.0 - 15.5", "flag": "L"}],
                     "fields": [{"testNameNormalized": "Haemoglobin"}], "needsReview": True,
                     "modelVersion": "test"},
    )
    monkeypatch.setattr(ml_client, "triage", lambda payload: {
        "acuity": "ROUTINE", "acuityConfidence": 0.6, "specialties": [], "drivers": [],
        "labs": [], "redFlags": [], "modelVersion": "stub"})
    r = client.post(
        "/v1/consultations/intake",
        json={"symptomText": "tired", "reportImageUris": ["reports/upload/u/a.webp"], "lang": "en"},
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert r.status_code == 200
    cid = uuid.UUID(r.json()["consultationId"])  # scope to THIS consultation — the DB has seeded reports
    rows = db.execute(select(Report).where(Report.consultation_id == cid)).scalars().all()
    assert len(rows) == 1
    saved = json.loads(rows[0].extraction_json)
    assert saved["needsReview"] is True
    assert saved["fields"][0]["testNameNormalized"] == "Haemoglobin"

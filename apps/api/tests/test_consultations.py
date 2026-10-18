import httpx


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

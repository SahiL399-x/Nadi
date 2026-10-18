import uuid

from app.models import Patient, User


def _token(client, phone, role, name):
    client.post("/v1/auth/request-otp", json={"phone": phone})
    r = client.post("/v1/auth/verify-otp",
                    json={"phone": phone, "code": "123456", "role": role, "name": name})
    return r.json()["accessToken"], r.json()["userId"]


def test_full_patient_doctor_pharmacy_loop(client, db, monkeypatch):
    from app.services import ml_client
    monkeypatch.setattr(ml_client, "document", lambda k: [])
    monkeypatch.setattr(ml_client, "triage", lambda p: {
        "acuity": "PRIORITY", "acuityConfidence": 0.8,
        "specialties": [{"name": "General Medicine", "score": 0.8},
                        {"name": "Cardiology", "score": 0.1}, {"name": "ENT", "score": 0.1}],
        "drivers": [{"feature": "x", "contribution": 0.5}], "labs": [],
        "redFlags": [], "modelVersion": "stub-keyword-v0"})

    # Unique phones per run: the suite commits to a persistent DB with no rollback
    # fixture, so fixed phone numbers would (a) collide with the same Patient PK on
    # a second run, raising an IntegrityError on the duplicate insert, and (b) make
    # the pharmacy inbox accumulate offers across runs, breaking the len == 1
    # assertion. Mirrors the fix already applied in test_pharmacies.py (c19316d).
    patient_phone = f"+91{uuid.uuid4().int % 10**10:010d}"
    doctor_phone = f"+91{uuid.uuid4().int % 10**10:010d}"
    pharmacy_phone = f"+91{uuid.uuid4().int % 10**10:010d}"

    pt, patient_id = _token(client, patient_phone, "patient", "E2E Patient")
    db.add(Patient(user_id=uuid.UUID(patient_id), age=40, sex="M"))
    db.commit()
    dt, doctor_id = _token(client, doctor_phone, "doctor", "E2E Doctor")
    pht, pharmacy_id = _token(client, pharmacy_phone, "pharmacy", "E2E Pharmacy")
    ph = {"Authorization": f"Bearer {pt}"}
    dh = {"Authorization": f"Bearer {dt}"}
    phh = {"Authorization": f"Bearer {pht}"}

    cid = client.post("/v1/consultations/intake",
                      json={"symptomText": "weakness", "reportImageUris": [],
                            "age": 40, "sex": "M", "lang": "en"}, headers=ph).json()["consultationId"]
    client.post(f"/v1/consultations/{cid}/book",
                json={"doctorId": doctor_id, "slot": "10:00"}, headers=ph)
    pres_id = client.post(f"/v1/doctor/consultations/{cid}/prescribe",
                          json={"lines": [{"drug": "Iron", "strength": "100mg",
                                           "frequency": "OD", "durationDays": 30}]},
                          headers=dh).json()["prescriptionId"]
    r = client.post(f"/v1/prescriptions/{pres_id}/consent",
                    json={"pharmacyIds": [pharmacy_id]}, headers=ph)
    assert r.status_code == 200
    inbox = client.get("/v1/pharmacy/inbox", headers=phh).json()
    assert len(inbox) == 1
    offer_id = inbox[0]["id"]
    acc = client.post(f"/v1/pharmacy/offers/{offer_id}/accept", headers=phh)
    assert acc.status_code == 200

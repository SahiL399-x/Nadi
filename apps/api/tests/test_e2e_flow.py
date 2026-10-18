import uuid

from app.models import Role, User


def _login(client, phone, name):
    """Patient self-signup: verify_otp creates the patient (and its profile row)."""
    client.post("/v1/auth/request-otp", json={"phone": phone})
    r = client.post("/v1/auth/verify-otp",
                    json={"phone": phone, "code": "123456", "name": name})
    return r.json()["accessToken"], r.json()["userId"]


def _provision_and_login(client, db, phone, role, name):
    """Providers are server-provisioned (seed/admin), then log in via OTP."""
    db.add(User(id=uuid.uuid4(), phone=phone, role=role, name=name))
    db.commit()
    client.post("/v1/auth/request-otp", json={"phone": phone})
    r = client.post("/v1/auth/verify-otp",
                    json={"phone": phone, "code": "123456", "name": name})
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

    pt, patient_id = _login(client, patient_phone, "E2E Patient")
    dt, doctor_id = _provision_and_login(client, db, doctor_phone, Role.doctor, "E2E Doctor")
    pht, pharmacy_id = _provision_and_login(client, db, pharmacy_phone, Role.pharmacy, "E2E Pharmacy")
    ph = {"Authorization": f"Bearer {pt}"}
    dh = {"Authorization": f"Bearer {dt}"}
    phh = {"Authorization": f"Bearer {pht}"}

    cid = client.post("/v1/consultations/intake",
                      json={"symptomText": "weakness", "reportImageUris": [],
                            "age": 40, "sex": "M", "lang": "en"}, headers=ph).json()["consultationId"]
    client.post(f"/v1/consultations/{cid}/book",
                json={"doctorId": doctor_id, "slot": "10:00"}, headers=ph)

    # A real (non-seeded) patient must appear in the doctor's queue, with the
    # age/sex carried from intake — this is the cross-device demo scenario.
    queue = client.get("/v1/doctor/queue", headers=dh).json()
    mine = [i for i in queue if i["id"] == cid]
    assert mine and mine[0]["patientName"] == "E2E Patient"
    assert mine[0]["patientAge"] == 40 and mine[0]["patientSex"] == "M"

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

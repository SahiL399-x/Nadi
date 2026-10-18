import uuid

from app.models import (
    Consultation, ConsultationStatus, Patient, Role, TriageResult, User,
)


def _doctor_token(client):
    client.post("/v1/auth/request-otp", json={"phone": "+918000000001"})
    r = client.post("/v1/auth/verify-otp",
                    json={"phone": "+918000000001", "code": "123456", "role": "doctor", "name": "Dr Q"})
    return r.json()["accessToken"], r.json()["userId"]


def test_queue_sorted_emergency_first(client, db):
    token, doctor_id = _doctor_token(client)
    pid = uuid.uuid4()
    db.add(User(id=pid, phone=f"+91{uuid.uuid4().int % 10**10:010d}", role=Role.patient, name="P"))
    db.flush()
    db.add(Patient(user_id=pid, age=40, sex="M"))
    for acuity in ("ROUTINE", "EMERGENCY"):
        cid = uuid.uuid4()
        db.add(Consultation(id=cid, patient_id=pid, doctor_id=doctor_id,
                            status=ConsultationStatus.BOOKED, symptom_text_raw="x", booked_for="10:00"))
        db.flush()
        db.add(TriageResult(id=uuid.uuid4(), consultation_id=cid, acuity=acuity,
                            acuity_confidence=0.9, specialties=[], drivers=[], red_flags=[],
                            model_version="stub-keyword-v0"))
    db.commit()
    r = client.get("/v1/doctor/queue", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()[0]["acuity"] == "EMERGENCY"

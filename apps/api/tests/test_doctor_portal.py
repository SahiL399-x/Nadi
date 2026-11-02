import uuid

from app.models import (
    Consultation, ConsultationStatus, Patient, Role, TriageResult, User,
)


def _doctor_token(client, db):
    # Providers are server-provisioned, then authenticate via OTP (unique phone per run).
    phone = f"+91{uuid.uuid4().int % 10**10:010d}"
    db.add(User(id=uuid.uuid4(), phone=phone, role=Role.doctor, name="Dr Q"))
    db.commit()
    client.post("/v1/auth/request-otp", json={"phone": phone})
    r = client.post("/v1/auth/verify-otp", json={"phone": phone, "code": "123456"})
    return r.json()["accessToken"], r.json()["userId"]


def test_queue_sorted_by_booked_time(client, db):
    import uuid
    from app.models import Consultation, ConsultationStatus, Patient, Role, TriageResult, User
    token, doctor_id = _doctor_token(client, db)
    pid = uuid.uuid4()
    db.add(User(id=pid, phone=f"+91{uuid.uuid4().int % 10**10:010d}", role=Role.patient, name="P"))
    db.flush()
    db.add(Patient(user_id=pid, age=40, sex="M"))
    for slot in ("14:00", "09:00"):
        cid = uuid.uuid4()
        db.add(Consultation(id=cid, patient_id=pid, doctor_id=doctor_id,
                            status=ConsultationStatus.BOOKED, symptom_text_raw="x", booked_for=slot))
        db.flush()
        db.add(TriageResult(id=uuid.uuid4(), consultation_id=cid, specialties=[], labs=[],
                            model_version="stub-keyword-v0"))
    db.commit()
    r = client.get("/v1/doctor/queue", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    bookings = [q["bookedFor"] for q in r.json()]
    assert bookings == sorted(bookings)


def test_appointments_expose_patient_id(client, doctor_token):
    h = {"Authorization": f"Bearer {doctor_token}"}
    rows = client.get("/v1/doctor/appointments", headers=h).json()
    assert rows, "seed should give the demo doctor appointments"
    assert all(r.get("patientId") for r in rows)


def test_queue_items_expose_patient_id(client, doctor_token):
    h = {"Authorization": f"Bearer {doctor_token}"}
    rows = client.get("/v1/doctor/queue", headers=h).json()
    assert all("patientId" in r for r in rows)

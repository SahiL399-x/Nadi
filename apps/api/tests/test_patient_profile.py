def test_profile_non_owner_denied_404(client, db):
    import uuid

    from sqlalchemy import select

    from app.models import Consultation, Role, User

    doc = db.scalar(select(User).where(User.phone == "+915000000001"))
    pid = str(db.scalar(select(Consultation.patient_id).where(Consultation.doctor_id == doc.id)))

    # A freshly-created doctor who has no consultation with this patient.
    phone = f"+91{uuid.uuid4().int % 10**10:010d}"
    db.add(User(id=uuid.uuid4(), phone=phone, role=Role.doctor, name="Dr Outsider"))
    db.commit()
    client.post("/v1/auth/request-otp", json={"phone": phone})
    r = client.post("/v1/auth/verify-otp", json={"phone": phone, "code": "123456"})
    token = r.json()["accessToken"]
    h = {"Authorization": f"Bearer {token}"}

    got = client.get(f"/v1/doctor/patients/{pid}", headers=h)
    assert got.status_code == 404


def test_profile_shape_for_owned_patient(client, doctor_token, db):
    from sqlalchemy import select

    from app.models import Consultation, User

    doc = db.scalar(select(User).where(User.phone == "+915000000001"))
    pid = str(db.scalar(select(Consultation.patient_id).where(Consultation.doctor_id == doc.id)))
    h = {"Authorization": f"Bearer {doctor_token}"}
    r = client.get(f"/v1/doctor/patients/{pid}", headers=h)
    assert r.status_code == 200
    assert {
        "name",
        "age",
        "sex",
        "conditions",
        "allergies",
        "familyHistory",
        "noKnownAllergies",
        "visits",
        "prescriptions",
    } <= set(r.json().keys())

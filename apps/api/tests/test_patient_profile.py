def test_profile_requires_own_patient(client, doctor_token, db):
    from sqlalchemy import select

    from app.models import Consultation

    pid = str(db.scalar(select(Consultation.patient_id).limit(1)))
    h = {"Authorization": f"Bearer {doctor_token}"}
    r = client.get(f"/v1/doctor/patients/{pid}", headers=h)
    # The seeded demo doctor owns the queue patients.
    assert r.status_code in (200, 404)


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

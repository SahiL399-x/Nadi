def test_doctor_can_add_and_list_notes(client, doctor_token, db):
    from sqlalchemy import select

    from app.models import Consultation, ConsultationStatus

    cid = str(
        db.scalar(
            select(Consultation.id).where(Consultation.status == ConsultationStatus.IN_PROGRESS)
        )
    )
    h = {"Authorization": f"Bearer {doctor_token}"}
    post = client.post(f"/v1/consultations/{cid}/notes", json={"text": "advised rest"}, headers=h)
    assert post.status_code == 200
    got = client.get(f"/v1/consultations/{cid}/notes", headers=h)
    assert got.status_code == 200
    assert any(n["text"] == "advised rest" for n in got.json())


def test_notes_are_private_per_author(client, doctor_token, db):
    """Each participant's notes are their own notebook: the doctor and the
    patient on the same consultation never see each other's notes."""
    from sqlalchemy import select

    from app.models import Consultation, ConsultationStatus, User

    consult = db.scalar(
        select(Consultation).where(Consultation.status == ConsultationStatus.IN_PROGRESS)
    )
    cid = str(consult.id)
    patient = db.get(User, consult.patient_id)
    # Log the consultation's own patient in.
    client.post("/v1/auth/request-otp", json={"phone": patient.phone})
    patient_token = client.post(
        "/v1/auth/verify-otp", json={"phone": patient.phone, "code": "123456"}
    ).json()["accessToken"]
    dh = {"Authorization": f"Bearer {doctor_token}"}
    ph = {"Authorization": f"Bearer {patient_token}"}

    client.post(f"/v1/consultations/{cid}/notes", json={"text": "doctor private note"}, headers=dh)
    client.post(f"/v1/consultations/{cid}/notes", json={"text": "patient private note"}, headers=ph)

    doc_notes = [n["text"] for n in client.get(f"/v1/consultations/{cid}/notes", headers=dh).json()]
    pat_notes = [n["text"] for n in client.get(f"/v1/consultations/{cid}/notes", headers=ph).json()]
    assert "doctor private note" in doc_notes and "patient private note" not in doc_notes
    assert "patient private note" in pat_notes and "doctor private note" not in pat_notes


def test_non_owner_denied_404(client, db):
    import uuid

    from sqlalchemy import select

    from app.models import Consultation, ConsultationStatus, Role, User

    cid = str(
        db.scalar(
            select(Consultation.id).where(Consultation.status == ConsultationStatus.IN_PROGRESS)
        )
    )
    # A freshly-created doctor who is neither the patient nor the assigned doctor.
    phone = f"+91{uuid.uuid4().int % 10**10:010d}"
    db.add(User(id=uuid.uuid4(), phone=phone, role=Role.doctor, name="Dr Outsider"))
    db.commit()
    client.post("/v1/auth/request-otp", json={"phone": phone})
    r = client.post("/v1/auth/verify-otp", json={"phone": phone, "code": "123456"})
    token = r.json()["accessToken"]
    h = {"Authorization": f"Bearer {token}"}

    got = client.get(f"/v1/consultations/{cid}/notes", headers=h)
    assert got.status_code == 404

    post = client.post(
        f"/v1/consultations/{cid}/notes", json={"text": "should not be allowed"}, headers=h
    )
    assert post.status_code == 404

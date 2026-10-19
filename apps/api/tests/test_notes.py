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

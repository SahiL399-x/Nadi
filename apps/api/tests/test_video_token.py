import uuid

from app.models import Consultation, ConsultationStatus, Role, User


def _patient(client):
    phone = f"+91{uuid.uuid4().int % 10**10:010d}"
    client.post("/v1/auth/request-otp", json={"phone": phone})
    r = client.post(
        "/v1/auth/verify-otp",
        json={"phone": phone, "code": "123456", "role": "patient", "name": "P"},
    )
    return r.json()["accessToken"], r.json()["userId"]


def _doctor(client, db):
    phone = f"+91{uuid.uuid4().int % 10**10:010d}"
    db.add(User(id=uuid.uuid4(), phone=phone, role=Role.doctor, name="Dr V"))
    db.commit()
    client.post("/v1/auth/request-otp", json={"phone": phone})
    r = client.post("/v1/auth/verify-otp", json={"phone": phone, "code": "123456"})
    return r.json()["accessToken"], r.json()["userId"]


def _consult(db, patient_id, doctor_id=None):
    cid = uuid.uuid4()
    db.add(
        Consultation(
            id=cid, patient_id=patient_id, doctor_id=doctor_id,
            status=ConsultationStatus.BOOKED, symptom_text_raw="x",
        )
    )
    db.commit()
    return str(cid)


def test_video_token_patient_participant_gets_token(client, db):
    token, pid = _patient(client)
    cid = _consult(db, uuid.UUID(pid))
    r = client.post(
        "/v1/video/token",
        headers={"Authorization": f"Bearer {token}"},
        json={"consultationId": cid},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["room"] == f"nadi-{cid}"
    assert body["url"].startswith("ws")
    # A LiveKit token is a JWT: three dot-separated segments, non-empty.
    assert body["token"].count(".") == 2


def test_video_token_assigned_doctor_gets_token(client, db):
    _, pid = _patient(client)
    dtoken, did = _doctor(client, db)
    cid = _consult(db, uuid.UUID(pid), doctor_id=uuid.UUID(did))
    r = client.post(
        "/v1/video/token",
        headers={"Authorization": f"Bearer {dtoken}"},
        json={"consultationId": cid},
    )
    assert r.status_code == 200


def test_video_token_non_participant_forbidden(client, db):
    _, owner_pid = _patient(client)
    intruder_token, _ = _patient(client)
    cid = _consult(db, uuid.UUID(owner_pid))
    r = client.post(
        "/v1/video/token",
        headers={"Authorization": f"Bearer {intruder_token}"},
        json={"consultationId": cid},
    )
    assert r.status_code == 404


def test_video_token_requires_auth(client):
    r = client.post("/v1/video/token", json={"consultationId": str(uuid.uuid4())})
    assert r.status_code == 401

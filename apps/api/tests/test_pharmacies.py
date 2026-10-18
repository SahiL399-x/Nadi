import uuid

from app.models import (
    Consultation, Prescription, Role, User,
)


def _pharmacy_token(client, phone):
    client.post("/v1/auth/request-otp", json={"phone": phone})
    r = client.post("/v1/auth/verify-otp",
                    json={"phone": phone, "code": "123456", "role": "pharmacy", "name": "Ph"})
    return r.json()["accessToken"], r.json()["userId"]


def test_decline_forwards_to_next_pharmacy(client, db):
    t1, ph1 = _pharmacy_token(client, "+917000000001")
    t2, ph2 = _pharmacy_token(client, "+917000000002")
    pat = uuid.uuid4()
    db.add(User(id=pat, phone=f"+91{uuid.uuid4().int % 10**10:010d}", role=Role.patient, name="P"))
    db.flush()
    cid, prid = uuid.uuid4(), uuid.uuid4()
    db.add(Consultation(id=cid, patient_id=pat))
    db.flush()
    db.add(Prescription(id=prid, consultation_id=cid))
    db.commit()
    from app.services import pharmacy_service
    pharmacy_service.grant_consent(db, prid, [ph1, ph2])

    inbox1 = client.get("/v1/pharmacy/inbox", headers={"Authorization": f"Bearer {t1}"}).json()
    assert len(inbox1) == 1
    offer_id = inbox1[0]["id"]
    r = client.post(f"/v1/pharmacy/offers/{offer_id}/decline",
                    headers={"Authorization": f"Bearer {t1}"})
    assert r.json()["forwarded"] is True
    inbox2 = client.get("/v1/pharmacy/inbox", headers={"Authorization": f"Bearer {t2}"}).json()
    assert len(inbox2) == 1

import uuid

from app.models import (
    Consultation, Prescription, Role, User,
)


def _pharmacy_token(client, db, phone):
    # Pharmacies are server-provisioned, then authenticate via OTP.
    db.add(User(id=uuid.uuid4(), phone=phone, role=Role.pharmacy, name="Ph"))
    db.commit()
    client.post("/v1/auth/request-otp", json={"phone": phone})
    r = client.post("/v1/auth/verify-otp", json={"phone": phone, "code": "123456"})
    return r.json()["accessToken"], r.json()["userId"]


def test_decline_forwards_to_next_pharmacy(client, db):
    # Unique phones per run -> fresh pharmacy users with clean inboxes.
    # The suite commits to a persistent DB with no rollback fixture, so reusing
    # fixed phone numbers would accumulate PENDING offers against the same users
    # and make the inbox-count assertions flaky across re-runs.
    t1, ph1 = _pharmacy_token(client, db, f"+91{uuid.uuid4().int % 10**10:010d}")
    t2, ph2 = _pharmacy_token(client, db, f"+91{uuid.uuid4().int % 10**10:010d}")
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


def test_list_pharmacies_returns_seeded_sorted_by_distance(client):
    r = client.get("/v1/pharmacies", params={"lat": 19.9975, "lng": 73.7898, "radiusKm": 50})
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 5
    dists = [p["distanceKm"] for p in rows]
    assert dists == sorted(dists)
    assert {"id", "name", "distanceKm", "deliversInMins", "isOpen"} <= set(rows[0].keys())

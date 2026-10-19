def test_availability_get_and_profile(client, doctor_token):
    h = {"Authorization": f"Bearer {doctor_token}"}
    a = client.get("/v1/doctor/availability", headers=h)
    assert a.status_code == 200 and len(a.json()) == 7
    p = client.get("/v1/doctor/profile", headers=h)
    assert p.status_code == 200
    assert {"name", "specialty", "clinicAddress"} <= set(p.json().keys())


def test_profile_update(client, doctor_token):
    h = {"Authorization": f"Bearer {doctor_token}"}
    client.put(
        "/v1/doctor/profile",
        json={"clinicAddress": "Panchavati, Nashik", "about": "Caring GP"},
        headers=h,
    )
    p = client.get("/v1/doctor/profile", headers=h).json()
    assert p["clinicAddress"] == "Panchavati, Nashik"


def test_put_availability_round_trips(client, doctor_token):
    h = {"Authorization": f"Bearer {doctor_token}"}
    days = client.get("/v1/doctor/availability", headers=h).json()
    days[0]["isOpen"] = False
    days[0]["morning"] = "10:00-12:00"

    r = client.put("/v1/doctor/availability", json={"days": days}, headers=h)
    assert r.status_code == 200
    updated = r.json()
    assert len(updated) == 7
    row0 = next(d for d in updated if d["weekday"] == days[0]["weekday"])
    assert row0["isOpen"] is False
    assert row0["morning"] == "10:00-12:00"

    persisted = client.get("/v1/doctor/availability", headers=h).json()
    row0_persisted = next(d for d in persisted if d["weekday"] == days[0]["weekday"])
    assert row0_persisted["isOpen"] is False
    assert row0_persisted["morning"] == "10:00-12:00"


def test_put_availability_isolated_per_doctor(client, db, doctor_token):
    from tests.test_doctor_portal import _doctor_token

    h = {"Authorization": f"Bearer {doctor_token}"}
    before = client.get("/v1/doctor/availability", headers=h).json()

    other_token, _ = _doctor_token(client, db)
    other_h = {"Authorization": f"Bearer {other_token}"}
    other_days = client.get("/v1/doctor/availability", headers=other_h).json()
    for d in other_days:
        d["isOpen"] = False
        d["morning"] = "00:00-00:00"
        d["evening"] = "00:00-00:00"
    r = client.put("/v1/doctor/availability", json={"days": other_days}, headers=other_h)
    assert r.status_code == 200

    after = client.get("/v1/doctor/availability", headers=h).json()
    assert after == before

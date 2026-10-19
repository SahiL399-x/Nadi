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

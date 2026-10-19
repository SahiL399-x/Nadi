def test_appointments_requires_doctor(client):
    assert client.get("/v1/doctor/appointments").status_code == 401


def test_appointments_returns_seeded_day(client, doctor_token):
    h = {"Authorization": f"Bearer {doctor_token}"}
    r = client.get("/v1/doctor/appointments", headers=h)
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 5
    statuses = {a["status"] for a in rows}
    assert statuses & {"Completed", "In Progress", "Arrived", "Upcoming"}
    assert {"id", "patientName", "time", "status"} <= set(rows[0].keys())

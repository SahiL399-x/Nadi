def test_doctor_stats_shape_and_counts(client, doctor_token):
    h = {"Authorization": f"Bearer {doctor_token}"}
    r = client.get("/v1/doctor/stats", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert {
        "appointmentsToday",
        "pending",
        "completed",
        "prescriptionsIssued",
        "newPatients",
    } == set(body)
    assert body["appointmentsToday"] >= 5
    assert body["prescriptionsIssued"] >= 1

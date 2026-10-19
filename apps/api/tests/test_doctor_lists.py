def test_doctor_prescriptions_list(client, doctor_token):
    h = {"Authorization": f"Bearer {doctor_token}"}
    r = client.get("/v1/doctor/prescriptions", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body  # demo doctor has ~6 seeded prescriptions
    assert {"id", "patientName", "issuedAt", "firstDrug", "status"} <= set(body[0].keys())


def test_doctor_prescriptions_list_status_filter(client, doctor_token):
    h = {"Authorization": f"Bearer {doctor_token}"}
    r = client.get("/v1/doctor/prescriptions", params={"status": "completed"}, headers=h)
    assert r.status_code == 200
    for item in r.json():
        assert item["status"] == "DELIVERED"


def test_doctor_lab_reports_list(client, doctor_token):
    h = {"Authorization": f"Bearer {doctor_token}"}
    r = client.get("/v1/doctor/lab-reports", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body  # seeded lab reports for the demo doctor's consultations
    assert {"id", "patientName", "date", "status"} <= set(body[0].keys())
    statuses = {item["status"] for item in body}
    assert "Completed" in statuses
    assert "Pending" in statuses


def test_doctor_lab_reports_list_status_filter(client, doctor_token):
    h = {"Authorization": f"Bearer {doctor_token}"}
    r = client.get("/v1/doctor/lab-reports", params={"status": "pending"}, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body
    for item in body:
        assert item["status"] == "Pending"

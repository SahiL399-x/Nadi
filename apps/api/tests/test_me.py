def test_me_endpoints_require_patient_and_return_lists(client, patient_token):
    h = {"Authorization": f"Bearer {patient_token}"}
    for path in ("/v1/me/appointments", "/v1/me/prescriptions", "/v1/me/reports"):
        r = client.get(path, headers=h)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


def test_me_appointments_requires_auth(client):
    assert client.get("/v1/me/appointments").status_code == 401

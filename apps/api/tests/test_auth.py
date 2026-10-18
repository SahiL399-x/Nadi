def test_verify_otp_with_stub_code_issues_tokens(client):
    client.post("/v1/auth/request-otp", json={"phone": "+919000000001"})
    r = client.post(
        "/v1/auth/verify-otp",
        json={"phone": "+919000000001", "code": "123456", "role": "patient", "name": "A"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["accessToken"] and body["role"] == "patient"


def test_wrong_code_rejected(client):
    r = client.post(
        "/v1/auth/verify-otp",
        json={"phone": "+919000000002", "code": "000000", "role": "patient", "name": "A"},
    )
    assert r.status_code == 401

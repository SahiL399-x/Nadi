def test_sign_returns_url_and_key(client, patient_token, monkeypatch):
    from app.services import storage_service
    monkeypatch.setattr(storage_service, "presign_put", lambda key: f"http://minio/{key}?sig=x")
    r = client.post("/v1/uploads/sign", headers={"Authorization": f"Bearer {patient_token}"})
    assert r.status_code == 200
    assert r.json()["url"].startswith("http")
    assert r.json()["objectKey"].startswith("reports/")

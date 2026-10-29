def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_sign_returns_url_and_key(client, patient_token, monkeypatch):
    from app.services import storage_service
    monkeypatch.setattr(storage_service, "presign_put", lambda key: f"http://minio/{key}?sig=x")
    r = client.post("/v1/uploads/sign", headers={"Authorization": f"Bearer {patient_token}"})
    assert r.status_code == 200
    assert r.json()["url"].startswith("http")
    assert r.json()["objectKey"].startswith("reports/")


def test_sign_defaults_to_upload_webp(client, patient_token, monkeypatch):
    from app.services import storage_service
    monkeypatch.setattr(storage_service, "presign_put", lambda key: f"http://minio/{key}?sig=x")
    r = client.post("/v1/uploads/sign", json={}, headers=_auth(patient_token))
    assert r.status_code == 200
    key = r.json()["objectKey"]
    assert key.startswith("reports/upload/")
    assert key.endswith(".webp")


def test_sign_scan_pdf_prefix_and_ext(client, patient_token, monkeypatch):
    from app.services import storage_service
    monkeypatch.setattr(storage_service, "presign_put", lambda key: f"http://minio/{key}?sig=x")
    r = client.post("/v1/uploads/sign", json={"source": "scan", "ext": "pdf"}, headers=_auth(patient_token))
    key = r.json()["objectKey"]
    assert key.startswith("reports/scan/")
    assert key.endswith(".pdf")


def test_sign_rejects_bad_source(client, patient_token, monkeypatch):
    from app.services import storage_service
    monkeypatch.setattr(storage_service, "presign_put", lambda key: "x")
    r = client.post("/v1/uploads/sign", json={"source": "evil", "ext": "exe"}, headers=_auth(patient_token))
    assert r.status_code == 422

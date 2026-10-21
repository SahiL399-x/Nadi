def test_video_token_returns_join_token(client, patient_token):
    h = {"Authorization": f"Bearer {patient_token}"}
    r = client.post("/v1/video/token", headers=h, json={"consultationId": "abc-123"})
    assert r.status_code == 200
    body = r.json()
    assert body["room"] == "nadi-abc-123"
    assert body["url"].startswith("ws")
    # A LiveKit token is a JWT: three dot-separated segments, non-empty.
    assert body["token"].count(".") == 2


def test_video_token_requires_auth(client):
    r = client.post("/v1/video/token", json={"consultationId": "abc-123"})
    assert r.status_code == 401

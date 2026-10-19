def test_search_medicines_requires_doctor(client):
    r = client.get("/v1/medicines", params={"q": "para"})
    assert r.status_code == 401


def test_search_medicines_returns_matches(client, doctor_token):
    h = {"Authorization": f"Bearer {doctor_token}"}
    r = client.get("/v1/medicines", params={"q": "para"}, headers=h)
    assert r.status_code == 200
    names = [m["name"].lower() for m in r.json()]
    assert any("paracetamol" in n for n in names)
    assert {"id", "name", "strength", "form"} <= set(r.json()[0].keys())

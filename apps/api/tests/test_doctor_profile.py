def test_doctor_can_set_keywords_and_read_them_back(client, doctor_token):
    h = {"Authorization": f"Bearer {doctor_token}"}
    r = client.put("/v1/doctor/profile", headers=h, json={
        "keywords": ["Diabetes", "diabetes", " thyroid "], "qualifications": "MBBS, MD",
        "experienceYears": 12})
    assert r.status_code == 200
    body = r.json()
    assert body["keywords"] == ["diabetes", "thyroid"]   # normalized + deduped
    assert body["qualifications"] == "MBBS, MD"
    assert body["experienceYears"] == 12
    got = client.get("/v1/doctor/profile", headers=h).json()
    assert got["keywords"] == ["diabetes", "thyroid"]


def test_keywords_capped_at_15(client, doctor_token):
    h = {"Authorization": f"Bearer {doctor_token}"}
    r = client.put("/v1/doctor/profile", headers=h,
                   json={"keywords": [f"k{i}" for i in range(40)]})
    assert len(r.json()["keywords"]) == 15

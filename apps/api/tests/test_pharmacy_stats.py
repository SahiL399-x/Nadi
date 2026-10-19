def test_pharmacy_stats(client, pharmacy_token):
    h = {"Authorization": f"Bearer {pharmacy_token}"}
    r = client.get("/v1/pharmacy/stats", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert {"newOrders", "inProgress", "outForDelivery", "completedToday"} == set(body)
    assert body["newOrders"] >= 1

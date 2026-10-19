def test_orders_requires_pharmacy(client):
    assert client.get("/v1/pharmacy/orders").status_code == 401


def test_orders_board_returns_seeded_orders(client, pharmacy_token):
    h = {"Authorization": f"Bearer {pharmacy_token}"}
    r = client.get("/v1/pharmacy/orders", headers=h)
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 10
    assert {"id", "orderNo", "patientName", "itemsCount", "totalInr", "status", "placedAt"} <= set(
        rows[0].keys()
    )
    assert all(o["orderNo"].startswith("NP") for o in rows)

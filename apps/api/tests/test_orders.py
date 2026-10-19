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
    assert any(o["itemsCount"] >= 1 for o in rows)


def test_orders_invalid_status_no_500(client, pharmacy_token):
    h = {"Authorization": f"Bearer {pharmacy_token}"}
    r = client.get("/v1/pharmacy/orders", headers=h, params={"status": "bogus"})
    assert r.status_code == 200
    assert r.json() == []


def _first_order_in(client, h, status):
    rows = client.get("/v1/pharmacy/orders", params={"status": status}, headers=h).json()
    return rows[0]["id"] if rows else None


def test_advance_order_status(client, pharmacy_token):
    h = {"Authorization": f"Bearer {pharmacy_token}"}
    oid = _first_order_in(client, h, "pending")
    assert oid
    r = client.post(f"/v1/pharmacy/orders/{oid}/status", json={"status": "PREPARING"}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "PREPARING"


def test_illegal_transition_rejected(client, pharmacy_token):
    h = {"Authorization": f"Bearer {pharmacy_token}"}
    oid = _first_order_in(client, h, "delivered")
    if oid:
        r = client.post(f"/v1/pharmacy/orders/{oid}/status", json={"status": "PENDING"}, headers=h)
        assert r.status_code == 400

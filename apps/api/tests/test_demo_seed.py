"""Demo-seed regression: the seeded database must keep the doctor and pharmacy
dashboards full, so a future seed edit can't silently empty them.

Assertions are drift-tolerant: other tests in the suite mutate shared state
(e.g. advancing order statuses, issuing prescriptions), so we assert invariants
that survive those mutations rather than exact pristine counts. The numbers only
ever grow or move between buckets from the seeded baseline, never below it.
"""


def test_doctor_dashboard_is_full(client, doctor_token):
    h = {"Authorization": f"Bearer {doctor_token}"}
    stats = client.get("/v1/doctor/stats", headers=h).json()
    # Seed gives the demo doctor 8 appointments and 6 issued prescriptions; both
    # only grow (test patients don't attach to this doctor).
    assert stats["appointmentsToday"] >= 8
    assert stats["prescriptionsIssued"] >= 6
    appts = client.get("/v1/doctor/appointments", headers=h).json()
    assert len(appts) >= 8
    meds = client.get("/v1/medicines", params={"q": ""}, headers=h).json()
    assert len(meds) >= 20


def test_pharmacy_dashboard_is_full(client, pharmacy_token):
    h = {"Authorization": f"Bearer {pharmacy_token}"}
    stats = client.get("/v1/pharmacy/stats", headers=h).json()
    orders = client.get("/v1/pharmacy/orders", headers=h).json()
    # 53 lifecycle orders seeded; transitions move orders between buckets but
    # never reduce the total or the completed tally.
    assert len(orders) >= 30
    assert stats["completedToday"] >= 20
    # Advancing a PENDING order moves it from newOrders into inProgress, so the
    # raw newOrders count drifts down; their sum is the stable invariant.
    assert stats["newOrders"] + stats["inProgress"] >= 12

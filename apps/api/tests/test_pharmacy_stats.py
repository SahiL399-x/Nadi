from sqlalchemy import func, select

from app.models import OfferStatus, PharmacyOffer, User


def test_pharmacy_stats(client, pharmacy_token):
    h = {"Authorization": f"Bearer {pharmacy_token}"}
    r = client.get("/v1/pharmacy/stats", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert {"newOrders", "inProgress", "outForDelivery", "completedToday"} == set(body)
    assert body["newOrders"] >= 1


def test_pharmacy_stats_buckets_match_db(client, db, pharmacy_token):
    h = {"Authorization": f"Bearer {pharmacy_token}"}
    r = client.get("/v1/pharmacy/stats", headers=h)
    assert r.status_code == 200
    body = r.json()

    pharmacy = db.scalar(select(User).where(User.phone == "+915000020000"))
    assert pharmacy is not None
    pid = pharmacy.id

    def expected_count(*statuses):
        return (
            db.scalar(
                select(func.count())
                .select_from(PharmacyOffer)
                .where(PharmacyOffer.pharmacy_id == pid)
                .where(PharmacyOffer.status.in_(statuses))
            )
            or 0
        )

    assert body["newOrders"] == expected_count(OfferStatus.PENDING, OfferStatus.TO_VERIFY)
    assert body["inProgress"] == expected_count(
        OfferStatus.PREPARING, OfferStatus.VERIFIED, OfferStatus.ACCEPTED
    )
    assert body["outForDelivery"] == expected_count(OfferStatus.OUT_FOR_DELIVERY)
    assert body["completedToday"] == expected_count(OfferStatus.DELIVERED, OfferStatus.COMPLETED)

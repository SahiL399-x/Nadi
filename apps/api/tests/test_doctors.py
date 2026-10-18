import uuid

from geoalchemy2.elements import WKTElement

from app.models import Doctor, Role, User


def _make_doctor(db, name, specialty, lat, lng, fee):
    uid = uuid.uuid4()
    db.add(User(id=uid, phone=f"+91{uuid.uuid4().int % 10**10:010d}", role=Role.doctor, name=name))
    db.flush()
    db.add(Doctor(user_id=uid, specialty=specialty, qualifications="MBBS", reg_number="R1",
                  experience_years=5, fee_inr=fee, languages=["Hindi", "English"],
                  location=WKTElement(f"POINT({lng} {lat})", srid=4326),
                  rating=4.5, review_count=10, is_verified=True, photo_url="x"))
    db.commit()
    return uid


def test_search_orders_by_distance(client, db):
    # near Nashik centre 19.9975,73.7898
    _make_doctor(db, "Dr Near", "Cardiology", 19.99, 73.79, 400)
    _make_doctor(db, "Dr Far", "Cardiology", 20.30, 74.20, 500)
    r = client.get("/v1/doctors", params={"specialty": "Cardiology",
                                           "lat": 19.9975, "lng": 73.7898, "radiusKm": 100})
    assert r.status_code == 200
    names = [d["name"] for d in r.json()]
    assert names.index("Dr Near") < names.index("Dr Far")

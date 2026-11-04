import uuid
from app.models import Doctor, Role, User
from app.services import doctor_service

NASHIK_LAT, NASHIK_LNG = 19.9975, 73.7898


def _doc(db, name, specialty, rating, keywords):
    uid = uuid.uuid4()
    db.add(User(id=uid, phone=f"+91{uuid.uuid4().int % 10**10:010d}", role=Role.doctor, name=name))
    db.flush()
    db.add(Doctor(
        user_id=uid, specialty=specialty, qualifications="MBBS", reg_number="R",
        experience_years=5, fee_inr=300, languages=["English"], rating=rating,
        review_count=10, keywords=keywords,
        location=doctor_service._point(NASHIK_LAT, NASHIK_LNG),
    ))
    db.commit()
    return str(uid)


def test_keyword_hit_returns_matching_doctors_ranked_by_rating(db):
    low = _doc(db, "Dr Low", "General Medicine", 3.0, ["diabetes", "thyroid"])
    high = _doc(db, "Dr High", "General Medicine", 4.9, ["diabetes"])
    out = doctor_service.recommend(db, "diabetes", None, NASHIK_LAT, NASHIK_LNG, 50.0, None)
    ids = [d.id for d in out if d.id in {low, high}]
    assert ids == [high, low]  # higher rating first


def test_no_keyword_hit_falls_back_to_specialty(db):
    d = _doc(db, "Dr Derm", "Dermatology", 4.0, ["rash", "acne"])
    out = doctor_service.recommend(db, "xyzzy-nomatch", "Dermatology", NASHIK_LAT, NASHIK_LNG, 50.0, None)
    assert d in [x.id for x in out] or any(x.specialty == "Dermatology" for x in out)


def test_exact_and_substring_matches_both_returned(db):
    # Doctor A matches the query token exactly; doctor B only matches via
    # substring containment ("sugar" is a substring of "sugary"). Both must
    # appear in recommend() output — neither should be silently dropped.
    exact = _doc(db, "Dr Exact", "General Medicine", 4.0, ["sugar"])
    substring = _doc(db, "Dr Substring", "General Medicine", 4.0, ["sugary"])
    out = doctor_service.recommend(db, "sugar", None, NASHIK_LAT, NASHIK_LNG, 50.0, None)
    ids = {x.id for x in out}
    assert exact in ids
    assert substring in ids

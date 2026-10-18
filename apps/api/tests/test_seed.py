from sqlalchemy import select

from app.models import Doctor, Pharmacy, TriageResult
from seed.seed import run


def test_seed_inserts_doctors_pharmacies_and_all_acuities(db):
    run(db)
    doctors = db.scalars(select(Doctor)).all()
    pharmacies = db.scalars(select(Pharmacy)).all()
    acuities = {
        (t.acuity.value if hasattr(t.acuity, "value") else t.acuity)
        for t in db.scalars(select(TriageResult)).all()
    }
    assert len(doctors) >= 10
    assert len(pharmacies) >= 5
    assert {"ROUTINE", "PRIORITY", "URGENT", "EMERGENCY"}.issubset(acuities)


def test_seed_is_idempotent(db):
    run(db)
    first = len(db.scalars(select(Doctor)).all())
    run(db)
    assert len(db.scalars(select(Doctor)).all()) == first

from sqlalchemy import select

from app.models import Consultation, Doctor, Pharmacy, TriageResult, User
from seed.seed import run


def test_seed_inserts_doctors_pharmacies_and_specialty_triage(db):
    run(db)
    doctors = db.scalars(select(Doctor)).all()
    pharmacies = db.scalars(select(Pharmacy)).all()
    # Scope to the seed's own queue consultations (demo patient phone prefix) so
    # unrelated TriageResult rows committed by other tests sharing this DB don't
    # leak into the assertion.
    seeded_triage = db.scalars(
        select(TriageResult)
        .join(Consultation, Consultation.id == TriageResult.consultation_id)
        .join(User, User.id == Consultation.patient_id)
        .where(User.phone.like("+9150000300%"))
    ).all()
    assert len(doctors) >= 10
    assert len(pharmacies) >= 5
    assert seeded_triage
    for t in seeded_triage:
        assert t.specialties
        assert t.model_version


def test_seed_is_idempotent(db):
    run(db)
    first = len(db.scalars(select(Doctor)).all())
    run(db)
    assert len(db.scalars(select(Doctor)).all()) == first


def test_seeded_doctors_have_specialty_aligned_keywords(db):
    run(db)
    doctors = db.scalars(select(Doctor)).all()
    with_keywords = [d for d in doctors if d.keywords]
    assert with_keywords
    for d in with_keywords:
        for kw in d.keywords:
            assert kw == kw.lower()

    # A bulk-seeded (non-demo) General Medicine doctor carries the "fever"
    # routing term — checked on the bulk roster rather than the demo account
    # because other tests authenticate as the demo doctor and overwrite its
    # keywords via the profile API, which would make this assertion flaky.
    demo = db.scalar(
        select(Doctor)
        .join(User, User.id == Doctor.user_id)
        .where(User.phone == "+915000000001")
    )
    assert demo is not None
    assert demo.keywords

    gen_med = next(
        d for d in doctors if d.specialty == "General Medicine" and d.user_id != demo.user_id
    )
    assert "fever" in gen_med.keywords

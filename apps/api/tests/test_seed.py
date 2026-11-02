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

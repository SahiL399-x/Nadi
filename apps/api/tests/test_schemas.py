from app.schemas.common import TriageResultOut
from app.schemas.doctor import DoctorOut


def test_triage_result_shape():
    t = TriageResultOut(
        specialties=[], labs=[], modelVersion="stub-keyword-v0",
    )
    assert t.model_dump()["modelVersion"] == "stub-keyword-v0"


def test_triage_result_out_is_specialty_only():
    assert set(TriageResultOut.model_fields) == {"specialties", "labs", "modelVersion"}


def test_doctor_requires_camelcase_fields():
    d = DoctorOut(
        id="1", name="Dr A", specialty="Cardiology", qualifications="MBBS",
        experienceYears=5, distanceKm=3.2, lat=19.99, lng=73.79, feeInr=400, rating=4.5,
        reviewCount=12, languages=["Hindi"], nextSlot="10:00",
        photoUrl="x", availableSlots=["10:00", "10:30"],
    )
    assert d.model_dump()["distanceKm"] == 3.2

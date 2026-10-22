import json
import pathlib
import uuid
from datetime import UTC, datetime

from geoalchemy2.elements import WKTElement
from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import (
    Consultation,
    ConsultationStatus,
    Doctor,
    Medicine,
    OfferStatus,
    Patient,
    PatientCondition,
    PatientVisit,
    Pharmacy,
    PharmacyOffer,
    Prescription,
    PrescriptionLine,
    PrescriptionStatus,
    Report,
    Role,
    TriageResult,
    User,
)

import random as _random

# Searchable specialties — each gets a full roster so any search returns 10+ doctors.
_SPECIALTIES = [
    "General Physician", "General Medicine", "Cardiology", "Dermatology",
    "Paediatrics", "Gynaecology", "Orthopaedics", "ENT", "Haematology",
]
_MALE = ["Rohan", "Arjun", "Vikram", "Sanjay", "Amit", "Rahul", "Nikhil", "Suresh", "Deepak", "Manoj", "Ravi", "Ajay", "Kiran", "Prakash", "Anil"]
_FEMALE = ["Anjali", "Sneha", "Priya", "Pooja", "Kavita", "Neha", "Divya", "Meera", "Shruti", "Aarti", "Swati", "Nisha", "Sunita", "Deepa", "Rekha"]
_SURNAMES = ["Deshmukh", "Kulkarni", "Patil", "Joshi", "Nair", "Rao", "Iyer", "Shah", "Mehta", "Gupta", "Reddy", "Verma", "Menon", "Bhat", "Desai"]
_LANG_SETS = [["Hindi", "Marathi", "English"], ["Hindi", "English"], ["Marathi", "English"], ["Hindi", "Marathi"]]
_QUALS = ["MBBS", "MBBS, MD", "MBBS, MD, DM", "MBBS, MS", "MBBS, DNB", "MBBS, MD, DNB"]


def _portrait(gender: str, n: int) -> str:
    # randomuser.me portraits: free, gender-labelled, stable per index.
    folder = "men" if gender == "M" else "women"
    return f"https://randomuser.me/api/portraits/{folder}/{n % 100}.jpg"


def _gen_doctors() -> list[tuple]:
    r = _random.Random(1234)  # deterministic -> idempotent reseeds
    out: list[tuple] = []
    mi = fi = 0
    for spec in _SPECIALTIES:
        for k in range(12):
            gender = "F" if k % 2 == 0 else "M"
            if gender == "M":
                first, photo, mi = _MALE[mi % len(_MALE)], _portrait("M", mi), mi + 1
            else:
                first, photo, fi = _FEMALE[fi % len(_FEMALE)], _portrait("F", fi), fi + 1
            out.append((
                f"Dr. {first} {r.choice(_SURNAMES)}", spec, r.choice(_QUALS), r.randint(5, 28),
                r.choice([300, 350, 400, 500, 600, 700, 800, 900, 1000, 1200]),
                round(r.uniform(4.1, 4.9), 1), r.randint(40, 420), r.choice(_LANG_SETS),
                19.9975 + r.uniform(-0.05, 0.05), 73.7898 + r.uniform(-0.05, 0.05), photo,
            ))
    return out


# (name, specialty, qual, exp, fee, rating, reviews, langs, lat, lng, photo)
DOCTORS = _gen_doctors()

PHARMACIES = [
    ("Nashik Medico", "MH-PH-1001", 19.9980, 73.7905, True, True),
    ("Godavari Pharmacy", "MH-PH-1002", 20.0100, 73.7890, True, True),
    ("Shree Medical Store", "MH-PH-1003", 19.9650, 73.8250, False, False),
    ("Panchavati Chemists", "MH-PH-1004", 20.0350, 73.7720, True, True),
    ("Trimurti Pharma", "MH-PH-1005", 19.9450, 73.7650, False, True),
]

MEDICINES = [
    ("Paracetamol", "500mg", "tablet"),
    ("Paracetamol", "650mg", "tablet"),
    ("Amoxicillin", "500mg", "capsule"),
    ("Azithromycin", "500mg", "tablet"),
    ("Amlodipine", "5mg", "tablet"),
    ("Metformin", "500mg", "tablet"),
    ("Pantoprazole", "40mg", "tablet"),
    ("Cetirizine", "10mg", "tablet"),
    ("Ibuprofen", "400mg", "tablet"),
    ("Omeprazole", "20mg", "capsule"),
    ("Atorvastatin", "10mg", "tablet"),
    ("Telmisartan", "40mg", "tablet"),
    ("Montelukast", "10mg", "tablet"),
    ("Levocetirizine", "5mg", "tablet"),
    ("Dolo", "650mg", "tablet"),
    ("Augmentin", "625mg", "tablet"),
    ("Pantocid", "40mg", "tablet"),
    ("Shelcal", "500mg", "tablet"),
    ("Thyronorm", "50mcg", "tablet"),
    ("Glimepiride", "1mg", "tablet"),
    ("Losartan", "50mg", "tablet"),
    ("Rosuvastatin", "10mg", "tablet"),
    ("Clopidogrel", "75mg", "tablet"),
    ("Aspirin", "75mg", "tablet"),
    ("Metoprolol", "25mg", "tablet"),
    ("Ramipril", "5mg", "capsule"),
    ("Cefixime", "200mg", "tablet"),
    ("Ofloxacin", "200mg", "tablet"),
    ("Domperidone", "10mg", "tablet"),
    ("Ondansetron", "4mg", "tablet"),
    ("Prednisolone", "10mg", "tablet"),
    ("Salbutamol", "100mcg", "inhaler"),
    ("Insulin", "100IU", "injection"),
    ("Cough Syrup", "100ml", "syrup"),
    ("ORS", "21.8g", "sachet"),
    ("Vitamin D3", "60000IU", "sachet"),
    ("B-Complex", "", "capsule"),
    ("Iron Folic Acid", "", "tablet"),
    ("Calcium", "500mg", "tablet"),
    ("Zincovit", "", "tablet"),
]

QUEUE = [
    ("Ramesh Pawar", 58, "M", "EMERGENCY", "chest pain and breathlessness"),
    ("Sunita Jadhav", 34, "F", "URGENT", "severe abdominal pain"),
    ("Imran Khan", 41, "M", "PRIORITY", "mujhe chakkar aa raha hai"),
    ("Lata More", 29, "F", "ROUTINE", "fever and cough for two days"),
    ("Vijay Shinde", 63, "M", "PRIORITY", "weakness and dizziness"),
    ("Pooja Deshpande", 7, "F", "ROUTINE", "mild cold"),
    ("Deepak Sharma", 45, "M", "ROUTINE", "back pain"),
    ("Anita Rao", 52, "F", "PRIORITY", "high blood pressure"),
]

# (status, hour, minute) — the demo doctor's day, in display order.
APPT_PLAN = [
    ("DONE", 9, 0),
    ("DONE", 9, 45),
    ("DONE", 10, 30),
    ("IN_PROGRESS", 11, 15),
    ("ARRIVED", 12, 0),
    ("BOOKED", 14, 0),
    ("BOOKED", 15, 30),
    ("BOOKED", 16, 45),
]


def _wkt(lat, lng):
    return WKTElement(f"POINT({lng} {lat})", srid=4326)


ORDER_SEED = {  # status -> count (dashboard targets; stats compute from these)
    "PENDING": 12,
    "PREPARING": 5,
    "VERIFIED": 3,
    "OUT_FOR_DELIVERY": 5,
    "DELIVERED": 15,
    "COMPLETED": 13,
}


def _seed_orders(db, pharmacy_uid):
    n = 4500
    for status, count in ORDER_SEED.items():
        for _ in range(count):
            pid = uuid.uuid4()
            db.add(
                User(
                    id=pid, phone=f"+9199{n:08d}", role=Role.patient, name=f"Patient {n}", lang="hi"
                )
            )
            db.flush()
            db.add(
                Patient(
                    user_id=pid,
                    age=30 + (n % 40),
                    sex="M" if n % 2 else "F",
                    location=_wkt(19.99, 73.79),
                )
            )
            cid = uuid.uuid4()
            db.add(
                Consultation(
                    id=cid,
                    patient_id=pid,
                    status=ConsultationStatus.DONE,
                    symptom_text_raw="follow-up",
                    symptom_text_normalised="follow-up",
                )
            )
            db.flush()
            pres = uuid.uuid4()
            if status in ("DELIVERED", "COMPLETED"):
                pres_status = PrescriptionStatus.DELIVERED
            elif status in ("ACCEPTED", "PREPARING", "VERIFIED", "OUT_FOR_DELIVERY"):
                pres_status = PrescriptionStatus.ACCEPTED
            else:
                pres_status = PrescriptionStatus.PENDING
            db.add(Prescription(id=pres, consultation_id=cid, status=pres_status))
            db.flush()
            db.add(
                PrescriptionLine(
                    id=uuid.uuid4(),
                    prescription_id=pres,
                    drug="Paracetamol",
                    strength="500mg",
                    frequency="BD",
                    duration_days=5,
                    notes=None,
                )
            )
            db.add(
                PharmacyOffer(
                    id=uuid.uuid4(),
                    prescription_id=pres,
                    pharmacy_id=pharmacy_uid,
                    status=OfferStatus[status],
                    rank=0,
                    order_no=f"NP{n}",
                )
            )
            n += 1


def run(db) -> None:
    if db.scalar(select(User).where(User.phone == "+915000000001")):
        return  # already seeded

    for i, (name, spec, qual, exp, fee, rating, reviews, langs, lat, lng, photo) in enumerate(DOCTORS):
        uid = uuid.uuid4()
        db.add(User(id=uid, phone=f"+9170{i:08d}", role=Role.doctor, name=name, lang="mr"))
        db.flush()
        db.add(
            Doctor(
                user_id=uid,
                specialty=spec,
                qualifications=qual,
                reg_number=f"MH{10000+i}",
                experience_years=exp,
                fee_inr=fee,
                languages=langs,
                location=_wkt(lat, lng),
                rating=rating,
                review_count=reviews,
                is_verified=True,
                photo_url=photo,
            )
        )

    demo_pharmacy_uid: uuid.UUID | None = None
    for i, (name, lic, lat, lng, delivers, is_open) in enumerate(PHARMACIES):
        uid = uuid.uuid4()
        db.add(User(id=uid, phone=f"+9150000200{i:02d}", role=Role.pharmacy, name=name, lang="mr"))
        db.flush()
        db.add(
            Pharmacy(
                user_id=uid,
                name=name,
                licence_number=lic,
                location=_wkt(lat, lng),
                delivers=delivers,
                is_open=is_open,
            )
        )
        if i == 0:
            demo_pharmacy_uid = uid

    # a demo doctor to own the queue
    doc_uid = uuid.uuid4()
    db.add(
        User(id=doc_uid, phone="+915000000001", role=Role.doctor, name="Dr. Rajiv Sharma", lang="en")
    )
    db.flush()
    db.add(
        Doctor(
            user_id=doc_uid,
            specialty="General Medicine",
            qualifications="MBBS, MD",
            reg_number="MH99999",
            experience_years=10,
            fee_inr=400,
            languages=["Hindi", "English"],
            location=_wkt(19.9975, 73.7898),
            rating=4.5,
            review_count=100,
            is_verified=True,
            photo_url="https://randomuser.me/api/portraits/men/32.jpg",
            clinic_address="Mital Nagar, Nashik",
            about="General physician, 10 years' experience.",
        )
    )
    db.flush()

    today = datetime.now(UTC).replace(
        microsecond=0
    )  # NOTE: seed runs at container start; fine for demo
    done_cids: list[uuid.UUID] = []
    for i, (pname, age, sex, acuity, complaint) in enumerate(QUEUE):
        pat_uid = uuid.uuid4()
        db.add(
            User(id=pat_uid, phone=f"+9150000300{i:02d}", role=Role.patient, name=pname, lang="hi")
        )
        db.flush()
        db.add(Patient(user_id=pat_uid, age=age, sex=sex, location=_wkt(19.99, 73.79)))
        cid = uuid.uuid4()
        db.flush()
        status, hh, mm = APPT_PLAN[i]
        sched = today.replace(hour=hh, minute=mm, second=0)
        db.add(
            Consultation(
                id=cid,
                patient_id=pat_uid,
                doctor_id=doc_uid,
                status=ConsultationStatus[status],
                symptom_text_raw=complaint,
                symptom_text_normalised=complaint,
                booked_for=f"{hh:02d}:{mm:02d}",
                scheduled_at=sched,
            )
        )
        db.flush()
        db.add(
            TriageResult(
                id=uuid.uuid4(),
                consultation_id=cid,
                acuity=acuity,
                acuity_confidence=0.9,
                specialties=[
                    {"name": "General Medicine", "score": 0.8},
                    {"name": "Cardiology", "score": 0.1},
                    {"name": "ENT", "score": 0.1},
                ],
                drivers=[{"feature": "symptom", "contribution": 0.5}],
                red_flags=["chest pain with breathlessness"] if acuity == "EMERGENCY" else [],
                model_version="stub-keyword-v0",
            )
        )
        if status == "DONE":
            done_cids.append(cid)

        if i == 0:  # give the first a rich history matching the mockup
            db.add(
                PatientCondition(
                    id=uuid.uuid4(), patient_id=pat_uid, label="Diabetes", kind="family_history"
                )
            )
        db.add(
            PatientVisit(
                id=uuid.uuid4(),
                patient_id=pat_uid,
                consultation_id=cid,
                visited_at="2025-10-16",
                summary=complaint,
                status="Completed",
            )
        )

    # issued prescriptions for the demo doctor's completed visits — 2 per DONE
    # consultation reaches the mockup's "Prescriptions Issued 6".
    PRES_LINES = [
        ("Paracetamol", "500mg", "BD", 5),
        ("Amoxicillin", "500mg", "TDS", 5),
    ]
    for idx, cid in enumerate(done_cids):
        # the first DONE consultation's prescriptions are seeded as already
        # delivered, so the demo doctor's ?status=completed filter is non-empty.
        pres_status = PrescriptionStatus.DELIVERED if idx == 0 else PrescriptionStatus.PENDING
        for drug, strength, frequency, duration_days in PRES_LINES:
            pres_id = uuid.uuid4()
            db.add(Prescription(id=pres_id, consultation_id=cid, status=pres_status))
            db.flush()
            db.add(
                PrescriptionLine(
                    id=uuid.uuid4(),
                    prescription_id=pres_id,
                    drug=drug,
                    strength=strength,
                    frequency=frequency,
                    duration_days=duration_days,
                    notes=None,
                )
            )

    # lab reports for the demo doctor's first two completed visits — one
    # finished (Completed) and one still processing (Pending) for the demo.
    for i, cid in enumerate(done_cids):
        if i < 2:
            db.add(
                Report(
                    id=uuid.uuid4(),
                    consultation_id=cid,
                    object_key=f"reports/seed-{i}.webp",
                    ocr_status="done" if i == 0 else "pending",
                )
            )

    for name, strength, form in MEDICINES:
        db.add(Medicine(name=name, strength=strength, form=form, is_common=True))

    if demo_pharmacy_uid is not None:
        _seed_orders(db, demo_pharmacy_uid)

    db.commit()


if __name__ == "__main__":
    session = SessionLocal()
    try:
        run(session)
        print("seeded")
    finally:
        session.close()

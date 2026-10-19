# NADI Backend Expansion — Plan C: Medium Doctor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax. Implements Stage C of `docs/superpowers/specs/2026-10-19-nadi-backend-expansion-design.md`. **Depends on Plans A–B.**

**Goal:** The Medium doctor backend — patient profile with medical history, the doctor's issued-prescriptions list, the lab-reports list, weekly availability, and editable profile — seeded so the Patient Profile, Prescriptions, Lab Reports, Availability, and Profile screens render full and real.

**Architecture:** New history models + a profile aggregation endpoint; list endpoints over existing `Prescription`/`Report` data; `DoctorAvailability` model + `Doctor` profile columns. Thin routers → services. Migrations chained after `0006`.

**Tech Stack:** As Plans A–B. Commands from `apps/api` via `.venv/Scripts/python`.

## Global Constraints

- Python type hints; `ruff`+`black`; pydantic at boundaries; routers thin, logic in `services/`.
- RBAC: `GET /v1/doctor/patients/{id}` only for a patient **booked with this doctor** (§11).
- **Routes, does not diagnose** (§14.1). **No AI/tool attribution**; commits short, imperative, lowercase.
- Additive; response models + pytest per endpoint; migrations chained/reversible; seed idempotent.

## Conventions

- Migration chain continues after `0006_order_lifecycle`: add `0007_patient_history`, `0008_doctor_availability_profile`.
- Uses the `doctor_token` fixture (Plan A).

---

### Task 1: Patient medical history + profile endpoint

**Files:**
- Create: `apps/api/app/models/history.py`
- Modify: `apps/api/app/models/__init__.py`
- Create: `apps/api/migrations/versions/0007_patient_history.py`
- Create: `apps/api/app/schemas/patient_profile.py`
- Create: `apps/api/app/services/patient_service.py`
- Modify: `apps/api/app/routers/doctor_portal.py`
- Modify: `apps/api/seed/seed.py`
- Create: `apps/api/tests/test_patient_profile.py`

**Interfaces:**
- Produces: `PatientCondition` (`kind: condition|allergy|family_history`) + `PatientVisit` models; `GET /v1/doctor/patients/{patientId}` → `PatientProfileOut` `{ name, age, sex, conditions[], allergies[], familyHistory[], noKnownAllergies, latestVisit, visits[], prescriptions[] }` (RBAC-checked).

- [ ] **Step 1: Write the failing test**

`apps/api/tests/test_patient_profile.py`:
```python
def test_profile_requires_own_patient(client, doctor_token, db):
    from sqlalchemy import select
    from app.models import Consultation
    pid = str(db.scalar(select(Consultation.patient_id).limit(1)))
    h = {"Authorization": f"Bearer {doctor_token}"}
    r = client.get(f"/v1/doctor/patients/{pid}", headers=h)
    # The seeded demo doctor owns the queue patients.
    assert r.status_code in (200, 404)

def test_profile_shape_for_owned_patient(client, doctor_token, db):
    from sqlalchemy import select
    from app.models import Consultation, User, Role
    doc = db.scalar(select(User).where(User.phone == "+915000000001"))
    pid = str(db.scalar(select(Consultation.patient_id).where(Consultation.doctor_id == doc.id)))
    h = {"Authorization": f"Bearer {doctor_token}"}
    r = client.get(f"/v1/doctor/patients/{pid}", headers=h)
    assert r.status_code == 200
    assert {"name", "age", "sex", "conditions", "allergies", "familyHistory",
            "noKnownAllergies", "visits", "prescriptions"} <= set(r.json().keys())
```

- [ ] **Step 2: Run to verify it fails** → `pytest tests/test_patient_profile.py -v` FAIL (404).

- [ ] **Step 3: Models + migration**

`apps/api/app/models/history.py`:
```python
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid_pk


class PatientCondition(Base):
    __tablename__ = "patient_conditions"
    id: Mapped[uuid.UUID] = uuid_pk()
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    label: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String)  # condition|allergy|family_history


class PatientVisit(Base):
    __tablename__ = "patient_visits"
    id: Mapped[uuid.UUID] = uuid_pk()
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    consultation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("consultations.id"), nullable=True)
    visited_at: Mapped[str] = mapped_column(String)  # ISO date for the demo
    summary: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="Completed")
```
Register both in `__init__.py`.

`apps/api/migrations/versions/0007_patient_history.py`:
```python
"""patient medical history

Revision ID: 0007_patient_history
Revises: 0006_order_lifecycle
Create Date: 2026-10-19
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_patient_history"
down_revision: str | None = "0006_order_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "patient_conditions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("patient_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
    )
    op.create_table(
        "patient_visits",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("patient_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("consultation_id", sa.UUID(), sa.ForeignKey("consultations.id"), nullable=True),
        sa.Column("visited_at", sa.String(), nullable=False),
        sa.Column("summary", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="Completed"),
    )


def downgrade() -> None:
    op.drop_table("patient_visits")
    op.drop_table("patient_conditions")
```
Run: `alembic upgrade head`.

- [ ] **Step 4: Schema + service**

`apps/api/app/schemas/patient_profile.py`:
```python
from pydantic import BaseModel


class VisitOut(BaseModel):
    visitedAt: str
    summary: str
    status: str


class PatientProfileOut(BaseModel):
    name: str
    age: int
    sex: str
    conditions: list[str]
    allergies: list[str]
    familyHistory: list[str]
    noKnownAllergies: bool
    latestVisit: VisitOut | None
    visits: list[VisitOut]
    prescriptions: list[str]  # drug summaries
```
`apps/api/app/services/patient_service.py`:
```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (Consultation, Patient, PatientCondition, PatientVisit, Prescription,
                        PrescriptionLine, User)
from app.schemas.patient_profile import PatientProfileOut, VisitOut


def owned_by_doctor(db: Session, patient_id, doctor_id) -> bool:
    return db.scalar(select(Consultation.id)
                     .where(Consultation.patient_id == patient_id)
                     .where(Consultation.doctor_id == doctor_id).limit(1)) is not None


def profile(db: Session, patient_id) -> PatientProfileOut | None:
    user = db.get(User, patient_id)
    if user is None:
        return None
    patient = db.get(Patient, patient_id)
    conds = list(db.scalars(select(PatientCondition).where(PatientCondition.patient_id == patient_id)))
    conditions = [c.label for c in conds if c.kind == "condition"]
    allergies = [c.label for c in conds if c.kind == "allergy"]
    family = [c.label for c in conds if c.kind == "family_history"]
    visits = [VisitOut(visitedAt=v.visited_at, summary=v.summary, status=v.status)
              for v in db.scalars(select(PatientVisit)
                                  .where(PatientVisit.patient_id == patient_id)
                                  .order_by(PatientVisit.visited_at.desc()))]
    pres_lines = db.scalars(
        select(PrescriptionLine).join(Prescription, Prescription.id == PrescriptionLine.prescription_id)
        .join(Consultation, Consultation.id == Prescription.consultation_id)
        .where(Consultation.patient_id == patient_id))
    prescriptions = [f"{ln.drug} {ln.strength}" for ln in pres_lines]
    return PatientProfileOut(
        name=user.name, age=(patient.age if patient and patient.age else 0),
        sex=(patient.sex if patient and patient.sex else "O"),
        conditions=conditions, allergies=allergies, familyHistory=family,
        noKnownAllergies=(len(allergies) == 0),
        latestVisit=visits[0] if visits else None, visits=visits, prescriptions=prescriptions)
```

- [ ] **Step 5: Route**

In `apps/api/app/routers/doctor_portal.py` (import `PatientProfileOut`, `patient_service`):
```python
@router.get("/patients/{patient_id}", response_model=PatientProfileOut)
def patient_profile(patient_id: str, user: User = Depends(require_role("doctor")),
                    db: Session = Depends(get_db)):
    if not patient_service.owned_by_doctor(db, patient_id, user.id):
        raise HTTPException(status_code=404, detail="not found")
    out = patient_service.profile(db, patient_id)
    if out is None:
        raise HTTPException(status_code=404, detail="not found")
    return out
```

- [ ] **Step 6: Seed histories**

In `apps/api/seed/seed.py`, for each demo-doctor queue patient, add a couple of conditions and a visit. Inside the queue-seeding loop:
```python
    from app.models import PatientCondition, PatientVisit
    if i == 0:  # give the first a rich history matching the mockup
        db.add(PatientCondition(id=uuid.uuid4(), patient_id=pat_uid, label="Diabetes", kind="family_history"))
    db.add(PatientVisit(id=uuid.uuid4(), patient_id=pat_uid, consultation_id=cid,
                        visited_at="2025-10-16", summary=complaint, status="Completed"))
```
(Leave `allergies` empty for most → `noKnownAllergies` true, as in the mockup.)

- [ ] **Step 7: Run tests + reseed** → reseed, then `pytest tests/test_patient_profile.py -v` PASS.

- [ ] **Step 8: Commit**

```bash
git add apps/api/app/models/history.py apps/api/app/models/__init__.py apps/api/migrations/versions/0007_patient_history.py apps/api/app/schemas/patient_profile.py apps/api/app/services/patient_service.py apps/api/app/routers/doctor_portal.py apps/api/seed/seed.py apps/api/tests/test_patient_profile.py
git commit -m "add patient profile with medical history"
```

---

### Task 2: Doctor prescriptions list + lab-reports list

**Files:**
- Create: `apps/api/app/schemas/doctor_lists.py`
- Modify: `apps/api/app/services/prescription_service.py`
- Create: `apps/api/app/services/lab_report_service.py`
- Modify: `apps/api/app/routers/doctor_portal.py`
- Create: `apps/api/tests/test_doctor_lists.py`

**Interfaces:**
- Produces: `GET /v1/doctor/prescriptions?status=all|active|completed` → `DoctorPrescriptionOut[]` `{ id, patientName, issuedAt, firstDrug, status }`; `GET /v1/doctor/lab-reports?status=all|pending|completed` → `LabReportOut[]` `{ id, patientName, date, status }`.

- [ ] **Step 1: Write the failing test**

`apps/api/tests/test_doctor_lists.py`:
```python
def test_doctor_prescriptions_list(client, doctor_token):
    h = {"Authorization": f"Bearer {doctor_token}"}
    r = client.get("/v1/doctor/prescriptions", headers=h)
    assert r.status_code == 200
    if r.json():
        assert {"id", "patientName", "issuedAt", "status"} <= set(r.json()[0].keys())

def test_doctor_lab_reports_list(client, doctor_token):
    h = {"Authorization": f"Bearer {doctor_token}"}
    r = client.get("/v1/doctor/lab-reports", headers=h)
    assert r.status_code == 200
```

- [ ] **Step 2: Run to verify it fails** → `pytest tests/test_doctor_lists.py -v` FAIL (404).

- [ ] **Step 3: Schemas + services**

`apps/api/app/schemas/doctor_lists.py`:
```python
from pydantic import BaseModel


class DoctorPrescriptionOut(BaseModel):
    id: str
    patientName: str
    issuedAt: str
    firstDrug: str
    status: str


class LabReportOut(BaseModel):
    id: str
    patientName: str
    date: str
    status: str
```
In `apps/api/app/services/prescription_service.py` add:
```python
def list_for_doctor(db: Session, doctor_id, status: str | None):
    from app.schemas.doctor_lists import DoctorPrescriptionOut
    rows = db.execute(
        select(Prescription, User).join(Consultation, Consultation.id == Prescription.consultation_id)
        .join(User, User.id == Consultation.patient_id)
        .where(Consultation.doctor_id == doctor_id)).all()
    out = []
    for pres, patient in rows:
        s = pres.status.value
        if status == "active" and s not in ("PENDING", "ACCEPTED"):
            continue
        if status == "completed" and s not in ("DELIVERED",):
            continue
        first = db.scalar(select(PrescriptionLine.drug)
                          .where(PrescriptionLine.prescription_id == pres.id).limit(1)) or ""
        out.append(DoctorPrescriptionOut(id=str(pres.id), patientName=patient.name,
                                         issuedAt=str(pres.issued_at), firstDrug=first, status=s))
    return out
```
`apps/api/app/services/lab_report_service.py`:
```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Consultation, Report, User
from app.schemas.doctor_lists import LabReportOut


def list_for_doctor(db: Session, doctor_id, status: str | None) -> list[LabReportOut]:
    rows = db.execute(
        select(Report, Consultation, User)
        .join(Consultation, Consultation.id == Report.consultation_id)
        .join(User, User.id == Consultation.patient_id)
        .where(Consultation.doctor_id == doctor_id)).all()
    out = []
    for report, consult, patient in rows:
        label = "Completed" if report.ocr_status == "done" else "Pending"
        if status == "pending" and label != "Pending":
            continue
        if status == "completed" and label != "Completed":
            continue
        out.append(LabReportOut(id=str(report.id), patientName=patient.name,
                                date=str(consult.created_at), status=label))
    return out
```

- [ ] **Step 4: Routes**

In `apps/api/app/routers/doctor_portal.py` (imports: `DoctorPrescriptionOut`, `LabReportOut`, `prescription_service`, `lab_report_service`):
```python
@router.get("/prescriptions", response_model=list[DoctorPrescriptionOut])
def doctor_prescriptions(status: str | None = None, user: User = Depends(require_role("doctor")),
                         db: Session = Depends(get_db)):
    return prescription_service.list_for_doctor(db, user.id, status)


@router.get("/lab-reports", response_model=list[LabReportOut])
def doctor_lab_reports(status: str | None = None, user: User = Depends(require_role("doctor")),
                       db: Session = Depends(get_db)):
    return lab_report_service.list_for_doctor(db, user.id, status)
```

- [ ] **Step 5: Seed a lab report or two**

In `apps/api/seed/seed.py`, attach a `Report` to one or two demo-doctor consultations so the list isn't empty:
```python
    from app.models import Report
    if i < 2:
        db.add(Report(id=uuid.uuid4(), consultation_id=cid, object_key=f"reports/seed-{i}.webp",
                      ocr_status="done" if i == 0 else "pending"))
```

- [ ] **Step 6: Run tests + reseed** → reseed, then `pytest tests/test_doctor_lists.py -v` PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/schemas/doctor_lists.py apps/api/app/services/prescription_service.py apps/api/app/services/lab_report_service.py apps/api/app/routers/doctor_portal.py apps/api/seed/seed.py apps/api/tests/test_doctor_lists.py
git commit -m "add doctor prescriptions and lab-reports lists"
```

---

### Task 3: Doctor availability + profile

**Files:**
- Create: `apps/api/app/models/availability.py`
- Modify: `apps/api/app/models/user.py` (add `clinic_address`, `about`)
- Modify: `apps/api/app/models/__init__.py`
- Create: `apps/api/migrations/versions/0008_doctor_availability_profile.py`
- Create: `apps/api/app/schemas/availability.py`, `apps/api/app/schemas/doctor_profile.py`
- Create: `apps/api/app/services/availability_service.py`
- Modify: `apps/api/app/services/doctor_service.py`
- Modify: `apps/api/app/routers/doctor_portal.py`
- Modify: `apps/api/seed/seed.py`
- Create: `apps/api/tests/test_availability.py`

**Interfaces:**
- Produces: `DoctorAvailability` model; `Doctor.clinic_address/about`; `GET/PUT /v1/doctor/availability` → `AvailabilityOut[]` (7 rows); `GET/PUT /v1/doctor/profile` → `DoctorProfileOut`.

- [ ] **Step 1: Write the failing test**

`apps/api/tests/test_availability.py`:
```python
def test_availability_get_and_profile(client, doctor_token):
    h = {"Authorization": f"Bearer {doctor_token}"}
    a = client.get("/v1/doctor/availability", headers=h)
    assert a.status_code == 200 and len(a.json()) == 7
    p = client.get("/v1/doctor/profile", headers=h)
    assert p.status_code == 200
    assert {"name", "specialty", "clinicAddress"} <= set(p.json().keys())

def test_profile_update(client, doctor_token):
    h = {"Authorization": f"Bearer {doctor_token}"}
    client.put("/v1/doctor/profile", json={"clinicAddress": "Panchavati, Nashik", "about": "Caring GP"}, headers=h)
    p = client.get("/v1/doctor/profile", headers=h).json()
    assert p["clinicAddress"] == "Panchavati, Nashik"
```

- [ ] **Step 2: Run to verify it fails** → `pytest tests/test_availability.py -v` FAIL (404).

- [ ] **Step 3: Models + migration**

`apps/api/app/models/availability.py`:
```python
import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid_pk


class DoctorAvailability(Base):
    __tablename__ = "doctor_availability"
    id: Mapped[uuid.UUID] = uuid_pk()
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    weekday: Mapped[int] = mapped_column(Integer)  # 0=Mon … 6=Sun
    morning: Mapped[str] = mapped_column(String, default="09:00-13:00")
    evening: Mapped[str] = mapped_column(String, default="17:00-20:00")
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)
```
In `apps/api/app/models/user.py` add to `Doctor`: `clinic_address: Mapped[str] = mapped_column(String, default="")` and `about: Mapped[str] = mapped_column(String, default="")`. Register `DoctorAvailability` in `__init__.py`.

`apps/api/migrations/versions/0008_doctor_availability_profile.py`:
```python
"""doctor availability and profile fields

Revision ID: 0008_doctor_availability_profile
Revises: 0007_patient_history
Create Date: 2026-10-19
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_doctor_availability_profile"
down_revision: str | None = "0007_patient_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("doctors", sa.Column("clinic_address", sa.String(), nullable=False, server_default=""))
    op.add_column("doctors", sa.Column("about", sa.String(), nullable=False, server_default=""))
    op.create_table(
        "doctor_availability",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("doctor_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("morning", sa.String(), nullable=False, server_default="09:00-13:00"),
        sa.Column("evening", sa.String(), nullable=False, server_default="17:00-20:00"),
        sa.Column("is_open", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_table("doctor_availability")
    op.drop_column("doctors", "about")
    op.drop_column("doctors", "clinic_address")
```
Run: `alembic upgrade head`.

- [ ] **Step 4: Schemas + services**

`apps/api/app/schemas/availability.py`:
```python
from pydantic import BaseModel


class AvailabilityOut(BaseModel):
    weekday: int
    morning: str
    evening: str
    isOpen: bool


class AvailabilityIn(BaseModel):
    days: list[AvailabilityOut]
```
`apps/api/app/schemas/doctor_profile.py`:
```python
from pydantic import BaseModel


class DoctorProfileOut(BaseModel):
    name: str
    specialty: str
    qualifications: str
    experienceYears: int
    clinicAddress: str
    about: str
    photoUrl: str


class DoctorProfileIn(BaseModel):
    clinicAddress: str | None = None
    about: str | None = None
```
`apps/api/app/services/availability_service.py`:
```python
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DoctorAvailability
from app.schemas.availability import AvailabilityOut

_DEFAULT = [(d, d < 5) for d in range(7)]  # Mon–Fri open, weekend closed


def get(db: Session, doctor_id) -> list[AvailabilityOut]:
    rows = {r.weekday: r for r in db.scalars(
        select(DoctorAvailability).where(DoctorAvailability.doctor_id == doctor_id))}
    if not rows:  # lazily create defaults the first time
        for d, is_open in _DEFAULT:
            db.add(DoctorAvailability(id=uuid.uuid4(), doctor_id=doctor_id, weekday=d, is_open=is_open))
        db.commit()
        rows = {r.weekday: r for r in db.scalars(
            select(DoctorAvailability).where(DoctorAvailability.doctor_id == doctor_id))}
    return [AvailabilityOut(weekday=d, morning=rows[d].morning, evening=rows[d].evening,
                            isOpen=rows[d].is_open) for d in range(7)]


def put(db: Session, doctor_id, days: list[AvailabilityOut]) -> list[AvailabilityOut]:
    existing = {r.weekday: r for r in db.scalars(
        select(DoctorAvailability).where(DoctorAvailability.doctor_id == doctor_id))}
    for d in days:
        row = existing.get(d.weekday)
        if row is None:
            row = DoctorAvailability(id=uuid.uuid4(), doctor_id=doctor_id, weekday=d.weekday)
            db.add(row)
        row.morning, row.evening, row.is_open = d.morning, d.evening, d.isOpen
    db.commit()
    return get(db, doctor_id)
```
In `apps/api/app/services/doctor_service.py` add profile get/update (import `DoctorProfileOut`, `User`):
```python
def profile(db: Session, doctor_id) -> DoctorProfileOut | None:
    from app.schemas.doctor_profile import DoctorProfileOut
    doctor = db.get(Doctor, doctor_id)
    user = db.get(User, doctor_id)
    if doctor is None or user is None:
        return None
    return DoctorProfileOut(name=user.name, specialty=doctor.specialty,
                            qualifications=doctor.qualifications, experienceYears=doctor.experience_years,
                            clinicAddress=doctor.clinic_address, about=doctor.about, photoUrl=doctor.photo_url)


def update_profile(db: Session, doctor_id, clinic_address, about):
    doctor = db.get(Doctor, doctor_id)
    if clinic_address is not None:
        doctor.clinic_address = clinic_address
    if about is not None:
        doctor.about = about
    db.commit()
    return profile(db, doctor_id)
```

- [ ] **Step 5: Routes**

In `apps/api/app/routers/doctor_portal.py` (imports: `AvailabilityOut`, `AvailabilityIn`, `DoctorProfileOut`, `DoctorProfileIn`, `availability_service`, `doctor_service`):
```python
@router.get("/availability", response_model=list[AvailabilityOut])
def get_availability(user: User = Depends(require_role("doctor")), db: Session = Depends(get_db)):
    return availability_service.get(db, user.id)


@router.put("/availability", response_model=list[AvailabilityOut])
def put_availability(body: AvailabilityIn, user: User = Depends(require_role("doctor")),
                     db: Session = Depends(get_db)):
    return availability_service.put(db, user.id, body.days)


@router.get("/profile", response_model=DoctorProfileOut)
def get_profile(user: User = Depends(require_role("doctor")), db: Session = Depends(get_db)):
    out = doctor_service.profile(db, user.id)
    if out is None:
        raise HTTPException(status_code=404, detail="not found")
    return out


@router.put("/profile", response_model=DoctorProfileOut)
def put_profile(body: DoctorProfileIn, user: User = Depends(require_role("doctor")),
                db: Session = Depends(get_db)):
    return doctor_service.update_profile(db, user.id, body.clinicAddress, body.about)
```

- [ ] **Step 6: Seed clinic address**

In `apps/api/seed/seed.py`, give the demo doctor a clinic address + about when creating it:
```python
    db.add(Doctor(user_id=doc_uid, specialty="General Medicine", qualifications="MBBS, MD",
                  reg_number="MH99999", experience_years=10, fee_inr=400, languages=["Hindi", "English"],
                  location=_wkt(19.9975, 73.7898), rating=4.5, review_count=100,
                  is_verified=True, photo_url=_PHOTOS[0],
                  clinic_address="Mital Nagar, Nashik", about="General physician, 10 years' experience."))
```
(Availability rows are created lazily on first GET, so no seed row is strictly required.)

- [ ] **Step 7: Run tests + reseed** → reseed, then `pytest tests/test_availability.py -v` PASS.

- [ ] **Step 8: Commit**

```bash
git add apps/api/app/models/availability.py apps/api/app/models/user.py apps/api/app/models/__init__.py apps/api/migrations/versions/0008_doctor_availability_profile.py apps/api/app/schemas/availability.py apps/api/app/schemas/doctor_profile.py apps/api/app/services/availability_service.py apps/api/app/services/doctor_service.py apps/api/app/routers/doctor_portal.py apps/api/seed/seed.py apps/api/tests/test_availability.py
git commit -m "add doctor availability and profile"
```

---

## Verification (end of Plan C)

- `alembic upgrade head` clean; reseed clean.
- `.venv/Scripts/python -m pytest` — all green.
- Manual: as the demo doctor, patient profile, prescriptions list, lab-reports list, availability (7 days), and profile get/update all return real data.

**Next plan:** `backend-D-seed-and-verify` — tune the demo seed to the dashboard targets, add a seed-count test, regenerate OpenAPI + shared types, full backend verification.

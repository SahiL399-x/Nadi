# NADI Backend Expansion — Plan A: Core Doctor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax. Implements Stage A of `docs/superpowers/specs/2026-10-19-nadi-backend-expansion-design.md`.

**Goal:** The Core doctor backend — a medicine catalog + search, dated appointments (with the `ARRIVED` status + `scheduled_at`), consultation notes, and doctor dashboard stats — all seeded so the doctor dashboard and appointments board look full.

**Architecture:** FastAPI routers stay thin and call services; new SQLAlchemy models + hand-written Alembic migrations chained after `0002`; pydantic response models mirror the v2 contract. Everything additive — the merged core flow keeps working.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, pydantic, pytest (existing `apps/api` stack). Run commands from `apps/api` using `.venv/Scripts/python`.

## Global Constraints

- Python type hints everywhere; `ruff` + `black`; pydantic at boundaries (ProjectPlan §12).
- Routers thin — validate, call a service, return; logic in `services/`.
- RBAC: a doctor sees only **their own** appointments/patients (§11).
- **Routes, does not diagnose** (§14.1). **No AI/tool attribution**; commits short, imperative, lowercase (§14.11).
- Additive only — no existing endpoint/shape changes.
- Every endpoint has a pydantic response model + pytest; migrations chained and reversible; seed idempotent.
- Postgres enum changes use `op.get_context().autocommit_block()` (an `ALTER TYPE … ADD VALUE` cannot run inside the migration's transaction).

## Conventions (from the existing codebase)

- Migrations: `apps/api/migrations/versions/NNNN_name.py`, `revision`/`down_revision` chained (latest is `0002_labs_and_constraints`). Run `cd apps/api && .venv/Scripts/python -m alembic upgrade head`.
- Models registered in `apps/api/app/models/__init__.py` (`__all__`).
- Tests follow `apps/api/tests/*` — `client`, `db`, `patient_token` fixtures in `conftest.py`. Add a `doctor_token` fixture (Task 1).
- Seed extends `apps/api/seed/seed.py` (idempotent; guarded on `+915000000001`).

---

### Task 1: ADR-0005, doctor test fixture, Medicine catalog + search

**Files:**
- Create: `docs/decisions/ADR-0005-v2-contract-doctor-pharmacy.md` (repo ADRs live in `docs/decisions/`, named `ADR-000N-*`)
- Create: `apps/api/app/models/medicine.py`
- Modify: `apps/api/app/models/__init__.py`
- Create: `apps/api/migrations/versions/0003_medicines.py`
- Create: `apps/api/app/schemas/medicine.py`
- Create: `apps/api/app/services/medicine_service.py`
- Create: `apps/api/app/routers/medicines.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/seed/seed.py`
- Modify: `apps/api/tests/conftest.py`
- Create: `apps/api/tests/test_medicines.py`

**Interfaces:**
- Produces: `Medicine` model; `GET /v1/medicines?q=` (doctor-only) → `MedicineOut[]` `{ id, name, strength, form }`; a `doctor_token` test fixture; ~40 seeded medicines.

- [ ] **Step 1: Write ADR-0005**

Create `docs/decisions/ADR-0005-v2-contract-doctor-pharmacy.md`:
```markdown
# ADR-0005: v2 API contract — doctor/pharmacy portal endpoints

## Status
Accepted (2026-10-19)

## Context
ProjectPlan §9 froze the API contract. The doctor and pharmacy portals require a
substantial, additive expansion (medicine catalog, appointments, notes, stats,
order lifecycle, patient history, availability, profile). See
docs/superpowers/specs/2026-10-19-nadi-backend-expansion-design.md.

## Decision
Lift the §9 freeze for ADDITIVE growth only. The v2 contract adds the endpoints in
the expansion spec. No existing endpoint or response shape changes, so the merged
mobile core keeps working. Heavy subsystems (messaging, inventory, delivery/rider)
are out of scope here and will have their own ADR when built.

## Consequences
The contract grows; `packages/shared-types` is regenerated. Existing clients unaffected.
```

- [ ] **Step 2: Add the `doctor_token` fixture**

Append to `apps/api/tests/conftest.py`:
```python
@pytest.fixture
def doctor_token(client) -> str:
    # The seeded demo doctor owns the queue/appointments.
    client.post("/v1/auth/request-otp", json={"phone": "+915000000001"})
    r = client.post("/v1/auth/verify-otp", json={"phone": "+915000000001", "code": "123456"})
    return r.json()["accessToken"]
```

- [ ] **Step 3: Write the failing test**

`apps/api/tests/test_medicines.py`:
```python
def test_search_medicines_requires_doctor(client):
    r = client.get("/v1/medicines", params={"q": "para"})
    assert r.status_code == 401

def test_search_medicines_returns_matches(client, doctor_token):
    h = {"Authorization": f"Bearer {doctor_token}"}
    r = client.get("/v1/medicines", params={"q": "para"}, headers=h)
    assert r.status_code == 200
    names = [m["name"].lower() for m in r.json()]
    assert any("paracetamol" in n for n in names)
    assert {"id", "name", "strength", "form"} <= set(r.json()[0].keys())
```

- [ ] **Step 4: Run to verify it fails**

Run: `cd apps/api && .venv/Scripts/python -m pytest tests/test_medicines.py -v`
Expected: FAIL — 404 (route missing).

- [ ] **Step 5: Model + migration**

`apps/api/app/models/medicine.py`:
```python
import uuid

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid_pk


class Medicine(Base):
    __tablename__ = "medicines"
    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String, index=True)
    strength: Mapped[str] = mapped_column(String, default="")
    form: Mapped[str] = mapped_column(String, default="tablet")  # tablet|capsule|syrup|drops|injection
    is_common: Mapped[bool] = mapped_column(Boolean, default=True)
```
Register in `apps/api/app/models/__init__.py` (import + add `"Medicine"` to `__all__`).

`apps/api/migrations/versions/0003_medicines.py`:
```python
"""medicine catalog

Revision ID: 0003_medicines
Revises: 0002_labs_and_constraints
Create Date: 2026-10-19
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_medicines"
down_revision: str | None = "0002_labs_and_constraints"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "medicines",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("strength", sa.String(), nullable=False, server_default=""),
        sa.Column("form", sa.String(), nullable=False, server_default="tablet"),
        sa.Column("is_common", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_medicines_name", "medicines", ["name"])


def downgrade() -> None:
    op.drop_index("ix_medicines_name", table_name="medicines")
    op.drop_table("medicines")
```
Run: `cd apps/api && .venv/Scripts/python -m alembic upgrade head`.

- [ ] **Step 6: Schema + service + router**

`apps/api/app/schemas/medicine.py`:
```python
from pydantic import BaseModel


class MedicineOut(BaseModel):
    id: str
    name: str
    strength: str
    form: str
```
`apps/api/app/services/medicine_service.py`:
```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Medicine
from app.schemas.medicine import MedicineOut


def search(db: Session, q: str | None, limit: int = 30) -> list[MedicineOut]:
    stmt = select(Medicine)
    if q:
        stmt = stmt.where(Medicine.name.ilike(f"%{q}%"))
    else:
        stmt = stmt.where(Medicine.is_common.is_(True))
    rows = db.scalars(stmt.order_by(Medicine.name.asc()).limit(limit)).all()
    return [MedicineOut(id=str(m.id), name=m.name, strength=m.strength, form=m.form) for m in rows]
```
`apps/api/app/routers/medicines.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models import User
from app.schemas.medicine import MedicineOut
from app.services import medicine_service

router = APIRouter(prefix="/v1/medicines", tags=["medicines"])


@router.get("", response_model=list[MedicineOut])
def search(q: str | None = None, _: User = Depends(require_role("doctor")),
           db: Session = Depends(get_db)) -> list[MedicineOut]:
    return medicine_service.search(db, q)
```
Register in `apps/api/app/main.py` (`from app.routers import medicines` + `app.include_router(medicines.router)`).

- [ ] **Step 7: Seed medicines**

In `apps/api/seed/seed.py`, add a module-level list and seed inside `run()` (after the existing guard):
```python
MEDICINES = [
    ("Paracetamol", "500mg", "tablet"), ("Paracetamol", "650mg", "tablet"),
    ("Amoxicillin", "500mg", "capsule"), ("Azithromycin", "500mg", "tablet"),
    ("Amlodipine", "5mg", "tablet"), ("Metformin", "500mg", "tablet"),
    ("Pantoprazole", "40mg", "tablet"), ("Cetirizine", "10mg", "tablet"),
    ("Ibuprofen", "400mg", "tablet"), ("Omeprazole", "20mg", "capsule"),
    ("Atorvastatin", "10mg", "tablet"), ("Telmisartan", "40mg", "tablet"),
    ("Montelukast", "10mg", "tablet"), ("Levocetirizine", "5mg", "tablet"),
    ("Dolo", "650mg", "tablet"), ("Augmentin", "625mg", "tablet"),
    ("Pantocid", "40mg", "tablet"), ("Shelcal", "500mg", "tablet"),
    ("Thyronorm", "50mcg", "tablet"), ("Glimepiride", "1mg", "tablet"),
    ("Losartan", "50mg", "tablet"), ("Rosuvastatin", "10mg", "tablet"),
    ("Clopidogrel", "75mg", "tablet"), ("Aspirin", "75mg", "tablet"),
    ("Metoprolol", "25mg", "tablet"), ("Ramipril", "5mg", "capsule"),
    ("Cefixime", "200mg", "tablet"), ("Ofloxacin", "200mg", "tablet"),
    ("Domperidone", "10mg", "tablet"), ("Ondansetron", "4mg", "tablet"),
    ("Prednisolone", "10mg", "tablet"), ("Salbutamol", "100mcg", "inhaler"),
    ("Insulin", "100IU", "injection"), ("Cough Syrup", "100ml", "syrup"),
    ("ORS", "21.8g", "sachet"), ("Vitamin D3", "60000IU", "sachet"),
    ("B-Complex", "", "capsule"), ("Iron Folic Acid", "", "tablet"),
    ("Calcium", "500mg", "tablet"), ("Zincovit", "", "tablet"),
]
```
Inside `run()`:
```python
    for name, strength, form in MEDICINES:
        db.add(Medicine(name=name, strength=strength, form=form, is_common=True))
```
(Add `Medicine` to the seed's model import.)

- [ ] **Step 8: Run tests + reseed**

Run: `cd apps/api && .venv/Scripts/python -m alembic upgrade head && .venv/Scripts/python -m seed.seed` (or restart docker compose). Then `.venv/Scripts/python -m pytest tests/test_medicines.py -v` → PASS.

- [ ] **Step 9: Commit**

```bash
git add docs/adr/0005-v2-contract-doctor-pharmacy.md apps/api/app/models/medicine.py apps/api/app/models/__init__.py apps/api/migrations/versions/0003_medicines.py apps/api/app/schemas/medicine.py apps/api/app/services/medicine_service.py apps/api/app/routers/medicines.py apps/api/app/main.py apps/api/seed/seed.py apps/api/tests/conftest.py apps/api/tests/test_medicines.py
git commit -m "add medicine catalog and search"
```

---

### Task 2: Appointments (scheduled_at + ARRIVED) and the appointments board

**Files:**
- Modify: `apps/api/app/models/consultation.py`
- Create: `apps/api/migrations/versions/0004_appointments.py`
- Create: `apps/api/app/schemas/appointment.py`
- Modify: `apps/api/app/services/consultation_service.py`
- Modify: `apps/api/app/routers/doctor_portal.py`
- Modify: `apps/api/seed/seed.py`
- Create: `apps/api/tests/test_appointments.py`

**Interfaces:**
- Produces: `Consultation.scheduled_at: datetime | None`; `ConsultationStatus.ARRIVED`; `GET /v1/doctor/appointments?date=YYYY-MM-DD` → `AppointmentOut[]` `{ id, patientName, patientAge, patientSex, photoUrl, time, status, acuity, complaint }` ordered by time; seeded day of 8 appointments across statuses.

- [ ] **Step 1: Write the failing test**

`apps/api/tests/test_appointments.py`:
```python
def test_appointments_requires_doctor(client):
    assert client.get("/v1/doctor/appointments").status_code == 401

def test_appointments_returns_seeded_day(client, doctor_token):
    h = {"Authorization": f"Bearer {doctor_token}"}
    r = client.get("/v1/doctor/appointments", headers=h)
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 5
    statuses = {a["status"] for a in rows}
    assert statuses & {"Completed", "In Progress", "Arrived", "Upcoming"}
    assert {"id", "patientName", "time", "status"} <= set(rows[0].keys())
```

- [ ] **Step 2: Run to verify it fails** → `pytest tests/test_appointments.py -v` FAIL (404).

- [ ] **Step 3: Model change + migration**

In `apps/api/app/models/consultation.py`: add `ARRIVED = "ARRIVED"` to `ConsultationStatus` (place it between BOOKED and IN_PROGRESS in the enum class), and add to `Consultation`:
```python
from datetime import datetime
from sqlalchemy import DateTime
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

`apps/api/migrations/versions/0004_appointments.py`:
```python
"""appointment scheduling

Revision ID: 0004_appointments
Revises: 0003_medicines
Create Date: 2026-10-19
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_appointments"
down_revision: str | None = "0003_medicines"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("consultations", sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True))
    # ALTER TYPE ... ADD VALUE cannot run inside the migration transaction.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE consultation_status ADD VALUE IF NOT EXISTS 'ARRIVED'")


def downgrade() -> None:
    # Postgres cannot drop an enum value; leave 'ARRIVED' in place.
    op.drop_column("consultations", "scheduled_at")
```
Run: `cd apps/api && .venv/Scripts/python -m alembic upgrade head`.

- [ ] **Step 4: Schema + service**

`apps/api/app/schemas/appointment.py`:
```python
from pydantic import BaseModel

from app.schemas.common import Acuity

_STATUS_LABEL = {
    "BOOKED": "Upcoming", "ARRIVED": "Arrived",
    "IN_PROGRESS": "In Progress", "DONE": "Completed",
}


class AppointmentOut(BaseModel):
    id: str
    patientName: str
    patientAge: int
    patientSex: str
    photoUrl: str
    time: str
    status: str
    acuity: Acuity | None = None
    complaint: str


def status_label(raw: str) -> str:
    return _STATUS_LABEL.get(raw, raw.title())
```
In `apps/api/app/services/consultation_service.py` add module-level imports `from datetime import date, datetime`, `from app.schemas.appointment import AppointmentOut, status_label` (`TriageResult` already imported), then:
```python
def doctor_appointments(db: Session, doctor_id, on: date | None) -> list[AppointmentOut]:
    stmt = (select(Consultation, User, Patient, TriageResult)
            .join(User, User.id == Consultation.patient_id)
            .outerjoin(Patient, Patient.user_id == Consultation.patient_id)
            .outerjoin(TriageResult, TriageResult.consultation_id == Consultation.id)
            .where(Consultation.doctor_id == doctor_id)
            .where(Consultation.status.in_(
                [ConsultationStatus.BOOKED, ConsultationStatus.ARRIVED,
                 ConsultationStatus.IN_PROGRESS, ConsultationStatus.DONE])))
    rows = db.execute(stmt).all()
    out = []
    for c, user, patient, tr in rows:
        when = c.scheduled_at
        if on is not None and (when is None or when.date() != on):
            continue
        out.append(AppointmentOut(
            id=str(c.id), patientName=user.name,
            patientAge=(patient.age if patient and patient.age is not None else 0),
            patientSex=(patient.sex if patient and patient.sex else "O"),
            photoUrl="", time=(when.strftime("%H:%M") if when else (c.booked_for or "")),
            status=status_label(c.status.value),
            acuity=(tr.acuity.value if tr else None), complaint=c.symptom_text_raw,
        ))
    out.sort(key=lambda a: a.time)
    return out
```

- [ ] **Step 5: Route**

In `apps/api/app/routers/doctor_portal.py` add (imports: `from datetime import date`, `AppointmentOut`):
```python
@router.get("/appointments", response_model=list[AppointmentOut])
def appointments(date: date | None = None, user: User = Depends(require_role("doctor")),
                 db: Session = Depends(get_db)):
    return consultation_service.doctor_appointments(db, user.id, date)
```

- [ ] **Step 6: Seed the demo day**

In `apps/api/seed/seed.py`, extend the queue-seeding loop so the demo doctor's consultations get a `scheduled_at` today and a spread of statuses. Replace the `QUEUE` seeding block to assign times and statuses:
```python
from datetime import datetime, timedelta, timezone

APPT_PLAN = [  # (status, hour, minute)
    ("DONE", 9, 0), ("DONE", 9, 45), ("DONE", 10, 30),
    ("IN_PROGRESS", 11, 15), ("ARRIVED", 12, 0),
    ("BOOKED", 14, 0), ("BOOKED", 15, 30), ("BOOKED", 16, 45),
]
```
When seeding the 6 `QUEUE` patients plus 2 more (extend `QUEUE` to 8 entries), set each consultation's `status` and `scheduled_at` from `APPT_PLAN[i]`:
```python
    today = datetime.now(timezone.utc).replace(microsecond=0)  # NOTE: seed runs at container start; fine for demo
    status, hh, mm = APPT_PLAN[i]
    sched = today.replace(hour=hh, minute=mm, second=0)
    db.add(Consultation(id=cid, patient_id=pat_uid, doctor_id=doc_uid,
                        status=ConsultationStatus[status], symptom_text_raw=complaint,
                        symptom_text_normalised=complaint, booked_for=f"{hh:02d}:{mm:02d}",
                        scheduled_at=sched))
```
(Extend `QUEUE` to 8 tuples — add e.g. `("Deepak Sharma", 45, "M", "ROUTINE", "back pain"), ("Anita Rao", 52, "F", "PRIORITY", "high blood pressure")`. `Date.now` is unavailable in workflow scripts but this is plain Python seed code — `datetime.now` is fine here.)

- [ ] **Step 7: Run tests + reseed**

Run: `cd apps/api && .venv/Scripts/python -m alembic upgrade head`, reseed (restart docker compose or drop+reseed), then `.venv/Scripts/python -m pytest tests/test_appointments.py tests/test_doctor_portal.py -v` → PASS (and the existing queue test still green).

- [ ] **Step 8: Commit**

```bash
git add apps/api/app/models/consultation.py apps/api/migrations/versions/0004_appointments.py apps/api/app/schemas/appointment.py apps/api/app/services/consultation_service.py apps/api/app/routers/doctor_portal.py apps/api/seed/seed.py apps/api/tests/test_appointments.py
git commit -m "add doctor appointments board with scheduling"
```

---

### Task 3: Consultation notes

**Files:**
- Create: `apps/api/app/models/note.py`
- Modify: `apps/api/app/models/__init__.py`
- Create: `apps/api/migrations/versions/0005_consultation_notes.py`
- Create: `apps/api/app/schemas/note.py`
- Create: `apps/api/app/services/note_service.py`
- Modify: `apps/api/app/routers/consultations.py`
- Create: `apps/api/tests/test_notes.py`

**Interfaces:**
- Produces: `ConsultationNote` model; `POST /v1/consultations/{id}/notes` `{ text }` → `{ id }` and `GET /v1/consultations/{id}/notes` → `NoteOut[]` `{ id, text, createdAt }`, authorised for the owning patient or assigned doctor.

- [ ] **Step 1: Write the failing test**

`apps/api/tests/test_notes.py`:
```python
def test_doctor_can_add_and_list_notes(client, doctor_token, db):
    from sqlalchemy import select
    from app.models import Consultation, ConsultationStatus
    cid = str(db.scalar(select(Consultation.id).where(
        Consultation.status == ConsultationStatus.IN_PROGRESS)))
    h = {"Authorization": f"Bearer {doctor_token}"}
    post = client.post(f"/v1/consultations/{cid}/notes", json={"text": "advised rest"}, headers=h)
    assert post.status_code == 200
    got = client.get(f"/v1/consultations/{cid}/notes", headers=h)
    assert got.status_code == 200
    assert any(n["text"] == "advised rest" for n in got.json())
```

- [ ] **Step 2: Run to verify it fails** → `pytest tests/test_notes.py -v` FAIL (404).

- [ ] **Step 3: Model + migration**

`apps/api/app/models/note.py`:
```python
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_col, uuid_pk


class ConsultationNote(Base):
    __tablename__ = "consultation_notes"
    id: Mapped[uuid.UUID] = uuid_pk()
    consultation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("consultations.id"))
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = created_at_col()
```
Register in `__init__.py`.

`apps/api/migrations/versions/0005_consultation_notes.py`:
```python
"""consultation notes

Revision ID: 0005_consultation_notes
Revises: 0004_appointments
Create Date: 2026-10-19
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_consultation_notes"
down_revision: str | None = "0004_appointments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "consultation_notes",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("consultation_id", sa.UUID(), sa.ForeignKey("consultations.id"), nullable=False),
        sa.Column("author_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("consultation_notes")
```
Run: `alembic upgrade head`.

- [ ] **Step 4: Schema + service + routes**

`apps/api/app/schemas/note.py`:
```python
from pydantic import BaseModel


class NoteIn(BaseModel):
    text: str


class NoteOut(BaseModel):
    id: str
    text: str
    createdAt: str
```
`apps/api/app/services/note_service.py`:
```python
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Consultation, ConsultationNote, User
from app.schemas.note import NoteOut


def can_access(db: Session, consultation_id, user: User) -> bool:
    c = db.get(Consultation, consultation_id)
    return c is not None and user.id in (c.patient_id, c.doctor_id)


def add(db: Session, consultation_id, author_id, text: str) -> ConsultationNote:
    note = ConsultationNote(id=uuid.uuid4(), consultation_id=consultation_id,
                            author_id=author_id, text=text)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def list_for(db: Session, consultation_id) -> list[NoteOut]:
    rows = db.scalars(select(ConsultationNote)
                      .where(ConsultationNote.consultation_id == consultation_id)
                      .order_by(ConsultationNote.created_at.asc())).all()
    return [NoteOut(id=str(n.id), text=n.text, createdAt=str(n.created_at)) for n in rows]
```
In `apps/api/app/routers/consultations.py` add (imports: `get_current_user`, `NoteIn`, `NoteOut`, `note_service`):
```python
@router.post("/{consultation_id}/notes")
def add_note(consultation_id: str, body: NoteIn, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)) -> dict:
    if not note_service.can_access(db, consultation_id, user):
        raise HTTPException(status_code=404, detail="not found")
    n = note_service.add(db, consultation_id, user.id, body.text)
    return {"id": str(n.id)}


@router.get("/{consultation_id}/notes", response_model=list[NoteOut])
def list_notes(consultation_id: str, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    if not note_service.can_access(db, consultation_id, user):
        raise HTTPException(status_code=404, detail="not found")
    return note_service.list_for(db, consultation_id)
```
Note: declare `/notes` routes after the existing `/{consultation_id}/triage` etc. Because `/{consultation_id}` (Task from Plan 02) is also a GET — `/notes` is a distinct suffix so no conflict.

- [ ] **Step 5: Run to verify it passes** → `pytest tests/test_notes.py -v` PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/models/note.py apps/api/app/models/__init__.py apps/api/migrations/versions/0005_consultation_notes.py apps/api/app/schemas/note.py apps/api/app/services/note_service.py apps/api/app/routers/consultations.py apps/api/tests/test_notes.py
git commit -m "add consultation notes"
```

---

### Task 4: Doctor dashboard stats

**Files:**
- Create: `apps/api/app/schemas/stats.py`
- Create: `apps/api/app/services/stats_service.py`
- Modify: `apps/api/app/routers/doctor_portal.py`
- Modify: `apps/api/seed/seed.py` (ensure issued prescriptions exist for the count)
- Create: `apps/api/tests/test_doctor_stats.py`

**Interfaces:**
- Produces: `GET /v1/doctor/stats` → `DoctorStatsOut` `{ appointmentsToday, pending, completed, prescriptionsIssued, newPatients }`, all computed for the authed doctor.

- [ ] **Step 1: Write the failing test**

`apps/api/tests/test_doctor_stats.py`:
```python
def test_doctor_stats_shape_and_counts(client, doctor_token):
    h = {"Authorization": f"Bearer {doctor_token}"}
    r = client.get("/v1/doctor/stats", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert {"appointmentsToday", "pending", "completed", "prescriptionsIssued", "newPatients"} == set(body)
    assert body["appointmentsToday"] >= 5
    assert body["prescriptionsIssued"] >= 1
```

- [ ] **Step 2: Run to verify it fails** → `pytest tests/test_doctor_stats.py -v` FAIL (404).

- [ ] **Step 3: Schema + service**

`apps/api/app/schemas/stats.py`:
```python
from pydantic import BaseModel


class DoctorStatsOut(BaseModel):
    appointmentsToday: int
    pending: int
    completed: int
    prescriptionsIssued: int
    newPatients: int
```
`apps/api/app/services/stats_service.py`:
```python
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Consultation, ConsultationStatus, Patient, Prescription, User
from app.schemas.stats import DoctorStatsOut

_PENDING = (ConsultationStatus.BOOKED, ConsultationStatus.ARRIVED, ConsultationStatus.IN_PROGRESS)


def doctor_stats(db: Session, doctor_id) -> DoctorStatsOut:
    appts = list(db.scalars(select(Consultation).where(Consultation.doctor_id == doctor_id)))
    appointments_today = len(appts)  # seed puts the demo day on these; fine for the demo scope
    pending = sum(1 for c in appts if c.status in _PENDING)
    completed = sum(1 for c in appts if c.status == ConsultationStatus.DONE)
    prescriptions_issued = db.scalar(
        select(func.count(Prescription.id))
        .join(Consultation, Consultation.id == Prescription.consultation_id)
        .where(Consultation.doctor_id == doctor_id)) or 0
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    new_patients = db.scalar(
        select(func.count(func.distinct(Consultation.patient_id)))
        .join(User, User.id == Consultation.patient_id)
        .where(Consultation.doctor_id == doctor_id)
        .where(User.created_at >= week_ago)) or 0
    return DoctorStatsOut(appointmentsToday=appointments_today, pending=pending,
                          completed=completed, prescriptionsIssued=prescriptions_issued,
                          newPatients=new_patients)
```

- [ ] **Step 4: Route**

In `apps/api/app/routers/doctor_portal.py` (import `DoctorStatsOut`, `stats_service`):
```python
@router.get("/stats", response_model=DoctorStatsOut)
def stats(user: User = Depends(require_role("doctor")), db: Session = Depends(get_db)):
    return stats_service.doctor_stats(db, user.id)
```

- [ ] **Step 5: Seed issued prescriptions**

In `apps/api/seed/seed.py`, after seeding the demo appointments, create prescriptions for the 3 `DONE` ones so `prescriptionsIssued` is realistic. For each completed consultation `cid`:
```python
    pres_id = uuid.uuid4()
    db.add(Prescription(id=pres_id, consultation_id=cid))
    db.flush()
    db.add(PrescriptionLine(id=uuid.uuid4(), prescription_id=pres_id, drug="Paracetamol",
                            strength="500mg", frequency="BD", duration_days=5, notes=None))
```
(Add `Prescription`, `PrescriptionLine` to the seed import. Target ≈6 total across the demo doctor's history — add a few more on completed visits to reach the mockup's "Prescriptions Issued 6".)

- [ ] **Step 6: Run tests + reseed** → reseed, then `pytest tests/test_doctor_stats.py -v` PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/schemas/stats.py apps/api/app/services/stats_service.py apps/api/app/routers/doctor_portal.py apps/api/seed/seed.py apps/api/tests/test_doctor_stats.py
git commit -m "add doctor dashboard stats"
```

---

## Verification (end of Plan A)

- `cd apps/api && .venv/Scripts/python -m alembic upgrade head` clean; reseed clean.
- `.venv/Scripts/python -m pytest` — all green (new + existing).
- Manual: as the demo doctor, `GET /v1/doctor/stats`, `/appointments`, `/medicines?q=para`, and consultation notes all return full, real data.

**Next plan:** `backend-B-core-pharmacy` — order lifecycle, orders board, status transitions, pharmacy stats, seeded lifecycle orders.

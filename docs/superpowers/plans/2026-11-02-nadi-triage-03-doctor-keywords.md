# Phase 3 — Doctor Profile Keywords Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give doctors a Fiverr-style self-managed keyword list (plus editable qualifications/experience) that the recommendation engine (Phase 4) matches patient queries against.

**Architecture:** Add a `keywords` string array to the `doctors` table. Extend `DoctorProfileIn/Out` and `doctor_service.update_profile` to read/write keywords (normalized, deduped, capped at 15) plus `qualifications` and `experienceYears`. Surface a chips editor in the doctor profile screen.

**Tech Stack:** Python/FastAPI/SQLAlchemy/Alembic/pydantic (api); Expo/RN + Zod (mobile).

## Global Constraints

- No AI attribution in any committed artefact.
- Keywords: lowercase-normalized, whitespace-trimmed, de-duplicated, **max 15** (excess truncated server-side).
- TDD; commit per task.
- api tests: `cd apps/api && ./.venv/Scripts/python.exe -m pytest` (DB up). mobile: `npm test` + `npm run typecheck`.

---

### Task 1: DB migration — `keywords` on `doctors`

**Files:**
- Create: `apps/api/migrations/versions/00NN_doctor_keywords.py`
- Test: `apps/api/tests/test_doctor_keywords.py` (new)

**Interfaces:**
- Produces: `doctors.keywords` — `ARRAY(String)`, NOT NULL, server default empty array.

> Set `down_revision` to the current head at build time (`alembic heads`). If Phase 5 landed
> first, chain after `0010_drop_acuity`; otherwise after `0009_report_extraction_json`. Name
> `00NN` accordingly (e.g. `0011_doctor_keywords`).

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_doctor_keywords.py
from sqlalchemy import inspect
from app.core.db import engine


def test_doctors_has_keywords_column():
    cols = {c["name"] for c in inspect(engine).get_columns("doctors")}
    assert "keywords" in cols
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/test_doctor_keywords.py -v`
Expected: FAIL — no `keywords` column.

- [ ] **Step 3: Write the migration**

```python
# apps/api/migrations/versions/0011_doctor_keywords.py
"""doctor keywords

Revision ID: 0011_doctor_keywords
Revises: 0010_drop_acuity
Create Date: 2026-11-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY

revision: str = "0011_doctor_keywords"
down_revision: str | None = "0010_drop_acuity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "doctors",
        sa.Column("keywords", ARRAY(sa.String()), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("doctors", "keywords")
```

- [ ] **Step 4: Apply + test**

Run:
```bash
docker compose -f infra/docker-compose.yml exec -T api alembic upgrade head
cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/test_doctor_keywords.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/migrations/versions/0011_doctor_keywords.py apps/api/tests/test_doctor_keywords.py
git commit -m "api: add keywords column to doctors"
```

---

### Task 2: Doctor model + keyword normalization helper

**Files:**
- Modify: `apps/api/app/models/user.py` (`Doctor` gets `keywords`)
- Create: `apps/api/app/services/keyword_util.py`
- Test: `apps/api/tests/test_keyword_util.py` (new)

**Interfaces:**
- Produces: `keyword_util.normalize_keywords(raw: list[str], cap: int = 15) -> list[str]` — lowercased, trimmed, non-empty, de-duplicated (order-preserving), truncated to `cap`.

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_keyword_util.py
from app.services.keyword_util import normalize_keywords


def test_lowercases_trims_dedupes_preserving_order():
    assert normalize_keywords([" Fever ", "COUGH", "fever", "cough"]) == ["fever", "cough"]


def test_drops_empties():
    assert normalize_keywords(["", "  ", "diabetes"]) == ["diabetes"]


def test_caps_at_limit():
    out = normalize_keywords([f"k{i}" for i in range(50)], cap=15)
    assert len(out) == 15
    assert out[0] == "k0"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/test_keyword_util.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement the helper**

```python
# apps/api/app/services/keyword_util.py
def normalize_keywords(raw: list[str], cap: int = 15) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        k = item.strip().lower()
        if k and k not in seen:
            seen.add(k)
            out.append(k)
        if len(out) >= cap:
            break
    return out
```

- [ ] **Step 4: Add the model column**

In `apps/api/app/models/user.py`, add to `Doctor` (after `languages`):
```python
    keywords: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
```
(`ARRAY` and `String` are already imported in that module.)

- [ ] **Step 5: Run the test**

Run: `cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/test_keyword_util.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/services/keyword_util.py apps/api/app/models/user.py apps/api/tests/test_keyword_util.py
git commit -m "api: Doctor.keywords model field + normalize_keywords helper"
```

---

### Task 3: Profile schema + service round-trip keywords/qualifications/experience

**Files:**
- Modify: `apps/api/app/schemas/doctor_profile.py`
- Modify: `apps/api/app/services/doctor_service.py` (`profile`, `update_profile`)
- Modify: `apps/api/app/routers/doctor_portal.py:125` (pass new fields)
- Test: `apps/api/tests/test_patient_profile.py` OR new `tests/test_doctor_profile.py`

**Interfaces:**
- Consumes: `keyword_util.normalize_keywords` (Task 2).
- Produces:
  - `DoctorProfileOut(name, specialty, qualifications, experienceYears, clinicAddress, about, photoUrl, keywords: list[str])`
  - `DoctorProfileIn(clinicAddress, about, qualifications, experienceYears, keywords)` — all optional.
  - `doctor_service.update_profile(db, doctor_id, *, clinic_address, about, qualifications, experience_years, keywords)` keyword-only args.

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_doctor_profile.py
def test_doctor_can_set_keywords_and_read_them_back(client, doctor_token):
    h = {"Authorization": f"Bearer {doctor_token}"}
    r = client.put("/v1/doctor/profile", headers=h, json={
        "keywords": ["Diabetes", "diabetes", " thyroid "], "qualifications": "MBBS, MD",
        "experienceYears": 12})
    assert r.status_code == 200
    body = r.json()
    assert body["keywords"] == ["diabetes", "thyroid"]   # normalized + deduped
    assert body["qualifications"] == "MBBS, MD"
    assert body["experienceYears"] == 12
    got = client.get("/v1/doctor/profile", headers=h).json()
    assert got["keywords"] == ["diabetes", "thyroid"]


def test_keywords_capped_at_15(client, doctor_token):
    h = {"Authorization": f"Bearer {doctor_token}"}
    r = client.put("/v1/doctor/profile", headers=h,
                   json={"keywords": [f"k{i}" for i in range(40)]})
    assert len(r.json()["keywords"]) == 15
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/test_doctor_profile.py -v`
Expected: FAIL — `keywords` not accepted/returned.

- [ ] **Step 3: Edit the schemas**

```python
# apps/api/app/schemas/doctor_profile.py
from pydantic import BaseModel


class DoctorProfileOut(BaseModel):
    name: str
    specialty: str
    qualifications: str
    experienceYears: int
    clinicAddress: str
    about: str
    photoUrl: str
    keywords: list[str] = []


class DoctorProfileIn(BaseModel):
    clinicAddress: str | None = None
    about: str | None = None
    qualifications: str | None = None
    experienceYears: int | None = None
    keywords: list[str] | None = None
```

- [ ] **Step 4: Edit `doctor_service.py`**

In `profile(...)` add `keywords=list(doctor.keywords)` to the returned `DoctorProfileOut`.
Replace `update_profile`:
```python
from app.services.keyword_util import normalize_keywords

def update_profile(db, doctor_id, *, clinic_address=None, about=None,
                   qualifications=None, experience_years=None, keywords=None):
    doctor = db.get(Doctor, doctor_id)
    if doctor is None:
        return None
    if clinic_address is not None:
        doctor.clinic_address = clinic_address
    if about is not None:
        doctor.about = about
    if qualifications is not None:
        doctor.qualifications = qualifications
    if experience_years is not None:
        doctor.experience_years = experience_years
    if keywords is not None:
        doctor.keywords = normalize_keywords(keywords)
    db.commit()
    return profile(db, doctor_id)
```

- [ ] **Step 5: Edit the router call** (`doctor_portal.py:125`)

```python
    out = doctor_service.update_profile(
        db, user.id, clinic_address=body.clinicAddress, about=body.about,
        qualifications=body.qualifications, experience_years=body.experienceYears,
        keywords=body.keywords,
    )
```

- [ ] **Step 6: Run the test**

Run: `cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/test_doctor_profile.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/schemas/doctor_profile.py apps/api/app/services/doctor_service.py apps/api/app/routers/doctor_portal.py apps/api/tests/test_doctor_profile.py
git commit -m "api: doctor profile reads/writes keywords, qualifications, experience"
```

---

### Task 4: Seed demo doctors with keywords

**Files:**
- Modify: `apps/api/seed/seed.py`
- Test: `apps/api/tests/test_seed.py`

- [ ] **Step 1: Add an assertion** that at least some seeded doctors have non-empty `keywords`
  (e.g. the demo doctor `+915000000001` has keywords including a routing term).

- [ ] **Step 2: Run it to verify it fails**

Run: `cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/test_seed.py -v`
Expected: FAIL.

- [ ] **Step 3: Edit `seed.py`** — give each seeded `Doctor` a small `keywords` list aligned to
  its specialty (e.g. Cardiology → `["chest pain","heart","palpitations","bp","hypertension"]`;
  General Medicine → `["fever","diabetes","thyroid","weakness","nausea"]`). Give the demo doctor
  a broad set so demo searches hit the keyword path.

- [ ] **Step 4: Reseed + test**

Run:
```bash
bash .superpowers/sdd/reseed.sh
cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/test_seed.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/seed/seed.py apps/api/tests/test_seed.py
git commit -m "api: seed doctors with specialty-aligned keywords"
```

---

### Task 5: mobile — keyword chips editor in doctor profile

**Files:**
- Modify: `apps/mobile/src/api/doctorPortal.ts` (`DoctorProfileSchema`, `updateDoctorProfile` body type)
- Modify: `apps/mobile/app/(doctor)/(tabs)/profile.tsx`
- Test: `apps/mobile/src/api/__tests__/doctorPortal.test.ts`

**Interfaces:**
- Consumes: `GET/PUT /v1/doctor/profile` now carrying `keywords`, `qualifications`, `experienceYears`.
- Produces: `DoctorProfile` type includes `keywords: string[]`.

- [ ] **Step 1: Update the schema test**

```ts
// apps/mobile/src/api/__tests__/doctorPortal.test.ts (add)
import { DoctorProfileSchema } from '../doctorPortal';

test('DoctorProfileSchema parses keywords', () => {
  const p = DoctorProfileSchema.parse({
    name: 'Dr A', specialty: 'Cardiology', qualifications: 'MBBS',
    experienceYears: 5, clinicAddress: '', about: '', photoUrl: '',
    keywords: ['chest pain', 'bp'],
  });
  expect(p.keywords).toEqual(['chest pain', 'bp']);
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd apps/mobile && npm test -- doctorPortal`
Expected: FAIL — `keywords` not in schema (Zod strips or the field is undefined).

- [ ] **Step 3: Edit `doctorPortal.ts`**
  - In `DoctorProfileSchema` (line ~33) add `keywords: z.array(z.string()).default([])`.
  - Change `updateDoctorProfile` body type to
    `{ clinicAddress?: string; about?: string; qualifications?: string; experienceYears?: number; keywords?: string[] }`.

- [ ] **Step 4: Edit `profile.tsx`** — add a chips editor: render each keyword as a removable
  chip, a text input + "Add" that appends (block past 15, trim/lowercase client-side for
  display), and include `keywords` in the `updateDoctorProfile` submit. Add inputs for
  `qualifications` and `experienceYears`. Follow the screen's existing input/styling patterns
  (direct `@/components/ui/*` imports, token colors — no raw hex).

- [ ] **Step 5: Typecheck + tests**

Run: `cd apps/mobile && npm run typecheck && npm test -- doctorPortal`
Expected: typecheck clean; test passes.

- [ ] **Step 6: Commit**

```bash
git add apps/mobile/src/api/doctorPortal.ts "apps/mobile/app/(doctor)/(tabs)/profile.tsx" apps/mobile/src/api/__tests__/doctorPortal.test.ts
git commit -m "mobile: doctor profile keyword chips + qualifications/experience editing"
```

## Self-review notes
- Spec Phase 3 coverage: DB (T1), model+normalizer (T2), schema+service+router (T3), seed (T4), mobile editor (T5). Covered.
- `qualifications`/`experienceYears` made editable per spec's "certifications/experience". `about`/`clinicAddress` already editable.
- Depends on Phase 5 only for migration chaining (down_revision); functionally independent.

# Phase 5 — Acuity Teardown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the `acuity` level, `acuityConfidence`, `drivers`, and red-flags from the entire app (ml-service + api + DB + mobile + shared-types), so triage routes to a specialty only, with no urgency signal.

**Architecture:** The triage contract becomes `{ specialties, labs, modelVersion }`. The DB drops three columns + the `drivers` column + the `acuity` enum type. The doctor queue, which sorted emergency-first, now sorts by `booked_for` ascending. Mobile loses the `AcuityBadge` and all acuity rendering.

**Tech Stack:** Python/FastAPI/SQLAlchemy/Alembic (api), pytest, pydantic; Python/FastAPI (ml-service); Expo/React Native + Zod + TypeScript (mobile).

## Global Constraints

- No AI attribution in any committed artefact (ProjectPlan §14.11).
- Flag-OFF (`ML_TRIAGE_ENABLED=false`) triage stub must return the new specialty-only shape after this phase.
- TDD throughout; commit per task.
- api host tests: `cd apps/api && ./.venv/Scripts/python.exe -m pytest`. DB must be up (`docker compose -f infra/docker-compose.yml up -d db`). Reseed: `bash .superpowers/sdd/reseed.sh`.
- ml-service host tests: `cd apps/ml-service && ./.venv/Scripts/python.exe -m pytest`.
- mobile: `cd apps/mobile && npm test` and `npm run typecheck`.

---

### Task 1: ml-service stub returns specialty-only; delete red-flags

**Files:**
- Modify: `apps/ml-service/app/triage_stub.py`
- Delete: `apps/ml-service/app/redflags.py`
- Test: `apps/ml-service/tests/test_triage_stub.py` (rewrite)

**Interfaces:**
- Produces: `triage_stub.run(symptom_text, labs, age, sex) -> {"specialties": [{name, score}], "labs": [...], "modelVersion": str}`. `MODEL_VERSION` unchanged (`"stub-keyword-v0"`).

- [ ] **Step 1: Rewrite the test to the new contract**

```python
# apps/ml-service/tests/test_triage_stub.py
from app.triage_stub import run


def test_skin_routes_to_dermatology():
    r = run("itchy rash on my arm", [], 28, "F")
    assert r["specialties"][0]["name"] == "Dermatology"


def test_chakkar_routes_to_general_medicine():
    r = run("mujhe chakkar aa raha hai", [], 30, "F")
    assert r["specialties"][0]["name"] == "General Medicine"


def test_chest_routes_to_cardiology():
    r = run("chest pain since morning", [], 45, "M")
    assert r["specialties"][0]["name"] == "Cardiology"


def test_contract_is_specialty_only():
    r = run("fever and cough", [], 25, "M")
    assert set(r.keys()) == {"specialties", "labs", "modelVersion"}
    assert r["modelVersion"] == "stub-keyword-v0"


def test_specialties_length_three_descending():
    r = run("something unmapped", [], 40, "M")
    scores = [s["score"] for s in r["specialties"]]
    assert len(r["specialties"]) == 3
    assert scores == sorted(scores, reverse=True)


def test_labs_passthrough():
    labs = [{"analyte": "Hb", "value": 9.1, "unit": "g/dL", "refRange": "12-15", "flag": "L"}]
    r = run("tired", labs, 40, "F")
    assert r["labs"] == labs
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd apps/ml-service && ./.venv/Scripts/python.exe -m pytest tests/test_triage_stub.py -v`
Expected: FAIL — current `run` returns `acuity`/`redFlags` keys, so `test_contract_is_specialty_only` fails.

- [ ] **Step 3: Rewrite `triage_stub.py` specialty-only**

```python
# apps/ml-service/app/triage_stub.py
MODEL_VERSION = "stub-keyword-v0"


def _specialties(primary: str, alts: list[str]) -> list[dict]:
    names = [primary, *alts][:3]
    scores = [0.82, 0.11, 0.07][: len(names)]
    return [{"name": n, "score": s} for n, s in zip(names, scores, strict=False)]


def _result(primary: str, alts: list[str], labs: list[dict]) -> dict:
    return {"specialties": _specialties(primary, alts), "labs": labs, "modelVersion": MODEL_VERSION}


# Ordered keyword rules (first match wins). Specialties limited to those with seeded
# doctors so "See doctors" always returns a list. English + common Hindi/Marathi terms.
# Deterministic stand-in for the trained model; it routes, it does not diagnose.
_RULES: list[tuple[tuple[str, ...], str, list[str]]] = [
    (("chest", "seene", "heart"), "Cardiology", ["General Medicine", "General Physician"]),
    (("rash", "itch", "skin", "daane", "pimple", "acne", "khujli"), "Dermatology", ["General Physician"]),
    (("ear", "nose", "throat", "gala", "sinus", "tonsil", "kaan", "naak"), "ENT", ["General Physician"]),
    (("period", "pregnan", "menstru", "gynae", "vaginal", "garbh", "mahvari"), "Gynaecology", ["General Medicine"]),
    (("child", "baby", "infant", "bachcha", "newborn", "toddler"), "Paediatrics", ["General Physician"]),
    (("joint", "knee", "back", "bone", "fracture", "sprain", "ghutna", "kamar", "haddi"), "Orthopaedics", ["General Medicine"]),
    (("chakkar", "dizzy", "weak", "weakness", "anaemi", "anemia", "pale", "thakan"), "General Medicine", ["Haematology", "Cardiology"]),
    (("fever", "cough", "cold", "bukhar", "khansi", "sardi"), "General Physician", ["ENT", "General Medicine"]),
    (("headache", "migraine", "sar dard", "sir dard"), "General Medicine", ["General Physician"]),
    (("stomach", "abdomen", "pet", "vomit", "nausea", "loose", "diarrh", "ulti", "dast"), "General Medicine", ["General Physician"]),
]


def run(symptom_text: str, labs: list[dict], age: int | None, sex: str | None) -> dict:
    t = symptom_text.lower()
    for keywords, primary, alts in _RULES:
        if any(k in t for k in keywords):
            return _result(primary, alts, labs)
    return _result("General Physician", ["General Medicine", "ENT"], labs)
```

- [ ] **Step 4: Delete the red-flags module**

```bash
git rm apps/ml-service/app/redflags.py
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd apps/ml-service && ./.venv/Scripts/python.exe -m pytest -v`
Expected: PASS (all ml-service tests; red-flag import is gone — confirm no other module imports `app.redflags`).

- [ ] **Step 6: Commit**

```bash
git add apps/ml-service/app/triage_stub.py apps/ml-service/tests/test_triage_stub.py
git commit -m "ml-service: triage stub returns specialty-only; remove red-flags"
```

---

### Task 2: DB migration drops acuity columns + enum

**Files:**
- Create: `apps/api/migrations/versions/0010_drop_acuity.py`
- Test: `apps/api/tests/test_triage_columns_dropped.py` (new)

**Interfaces:**
- Produces: `triage_results` table without columns `acuity`, `acuity_confidence`, `red_flags`, `drivers`; Postgres enum type `acuity` dropped.

> NOTE: set `down_revision` to the actual current migration head at build time
> (`alembic heads`). If Phase 3 already landed its keyword migration, chain after it.
> At the time of writing the head is `0009_report_extraction_json`.

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_triage_columns_dropped.py
from sqlalchemy import inspect
from app.core.db import engine


def test_triage_results_has_no_acuity_columns():
    cols = {c["name"] for c in inspect(engine).get_columns("triage_results")}
    assert "acuity" not in cols
    assert "acuity_confidence" not in cols
    assert "red_flags" not in cols
    assert "drivers" not in cols
    assert {"specialties", "labs", "model_version"} <= cols
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/test_triage_columns_dropped.py -v`
Expected: FAIL — columns still present.

- [ ] **Step 3: Write the migration**

```python
# apps/api/migrations/versions/0010_drop_acuity.py
"""drop acuity, acuity_confidence, red_flags, drivers from triage_results

Revision ID: 0010_drop_acuity
Revises: 0009_report_extraction_json
Create Date: 2026-11-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM, JSONB

revision: str = "0010_drop_acuity"
down_revision: str | None = "0009_report_extraction_json"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("triage_results", "acuity")
    op.drop_column("triage_results", "acuity_confidence")
    op.drop_column("triage_results", "red_flags")
    op.drop_column("triage_results", "drivers")
    ENUM(name="acuity").drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    acuity = ENUM("ROUTINE", "PRIORITY", "URGENT", "EMERGENCY", name="acuity")
    acuity.create(op.get_bind(), checkfirst=True)
    op.add_column("triage_results", sa.Column("acuity", acuity, nullable=True))
    op.add_column("triage_results", sa.Column("acuity_confidence", sa.Float(), nullable=True))
    op.add_column("triage_results", sa.Column("red_flags", JSONB(), nullable=True))
    op.add_column("triage_results", sa.Column("drivers", JSONB(), nullable=True))
```

- [ ] **Step 4: Apply the migration and run the test**

Run:
```bash
docker compose -f infra/docker-compose.yml exec -T api alembic upgrade head
cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/test_triage_columns_dropped.py -v
```
(If running the api on the host instead: `cd apps/api && ./.venv/Scripts/python.exe -m alembic upgrade head`.)
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/migrations/versions/0010_drop_acuity.py apps/api/tests/test_triage_columns_dropped.py
git commit -m "api: migration 0010 drops acuity/red_flags/drivers from triage_results"
```

---

### Task 3: api models + schemas specialty-only

**Files:**
- Modify: `apps/api/app/models/triage.py` (remove `Acuity` enum + 4 columns)
- Modify: `apps/api/app/schemas/common.py` (`TriageResultOut`, drop `Acuity`/`Driver` types)
- Modify: `apps/api/app/schemas/appointment.py:22` (drop `acuity`)
- Modify: `apps/api/app/schemas/consultation.py:22` (drop `acuity` from `QueueItemOut`)
- Test: `apps/api/tests/test_schemas.py` (update acuity assertions)

**Interfaces:**
- Produces: `TriageResultOut(specialties: list[SpecialtyScore], labs: list[LabValueOut], modelVersion: str)` with `from_model(tr)` building only those.

- [ ] **Step 1: Update `test_schemas.py`** — remove any assertions referencing `acuity`,
  `acuityConfidence`, `drivers`, `redFlags`; add:

```python
def test_triage_result_out_is_specialty_only():
    from app.schemas.common import TriageResultOut
    assert set(TriageResultOut.model_fields) == {"specialties", "labs", "modelVersion"}
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/test_schemas.py -v`
Expected: FAIL — extra fields present.

- [ ] **Step 3: Edit `app/models/triage.py`** — delete the `Acuity` enum class and the
  `acuity`, `acuity_confidence`, `red_flags`, `drivers` columns on `TriageResult`. Keep
  `specialties`, `labs`, `model_version`, `created_at`, ids.

- [ ] **Step 4: Edit `app/schemas/common.py`**

```python
class TriageResultOut(BaseModel):
    specialties: list[SpecialtyScore]
    labs: list[LabValueOut]
    modelVersion: str

    @classmethod
    def from_model(cls, tr) -> "TriageResultOut":
        return cls(
            specialties=tr.specialties or [],
            labs=tr.labs or [],
            modelVersion=tr.model_version,
        )
```
Remove the `Acuity = Literal[...]` and `class Driver` definitions (confirm no other importer; grep first).

- [ ] **Step 5: Edit `app/schemas/appointment.py`** — remove the `acuity: Acuity | None` field
  and its `Acuity` import. **Edit `app/schemas/consultation.py`** — remove `acuity: Acuity`
  from `QueueItemOut` and its import.

- [ ] **Step 6: Run the schema tests**

Run: `cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/test_schemas.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/models/triage.py apps/api/app/schemas/common.py apps/api/app/schemas/appointment.py apps/api/app/schemas/consultation.py apps/api/tests/test_schemas.py
git commit -m "api: triage model + schemas specialty-only (drop acuity/drivers/redFlags)"
```

---

### Task 4: consultation_service — queue by booked_for, no acuity writes

**Files:**
- Modify: `apps/api/app/services/consultation_service.py`
- Test: `apps/api/tests/test_doctor_portal.py` (replace `test_queue_sorted_emergency_first`)

**Interfaces:**
- Consumes: `TriageResult` without acuity (Task 3); `TriageResultOut` (Task 3).
- Produces: `doctor_queue` and `doctor_appointments` ordered by `booked_for` ascending; `intake` writes a `TriageResult` with only `specialties`, `labs`, `model_version`.

- [ ] **Step 1: Replace the queue-ordering test**

```python
# apps/api/tests/test_doctor_portal.py  (replace test_queue_sorted_emergency_first)
def test_queue_sorted_by_booked_time(client, db):
    import uuid
    from app.models import Consultation, ConsultationStatus, Patient, Role, TriageResult, User
    token, doctor_id = _doctor_token(client, db)
    pid = uuid.uuid4()
    db.add(User(id=pid, phone=f"+91{uuid.uuid4().int % 10**10:010d}", role=Role.patient, name="P"))
    db.flush()
    db.add(Patient(user_id=pid, age=40, sex="M"))
    for slot in ("14:00", "09:00"):
        cid = uuid.uuid4()
        db.add(Consultation(id=cid, patient_id=pid, doctor_id=doctor_id,
                            status=ConsultationStatus.BOOKED, symptom_text_raw="x", booked_for=slot))
        db.flush()
        db.add(TriageResult(id=uuid.uuid4(), consultation_id=cid, specialties=[], labs=[],
                            model_version="stub-keyword-v0"))
    db.commit()
    r = client.get("/v1/doctor/queue", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    bookings = [q["bookedFor"] for q in r.json()]
    assert bookings == sorted(bookings)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/test_doctor_portal.py::test_queue_sorted_by_booked_time -v`
Expected: FAIL — `TriageResult(...)` still requires acuity (before Task 3 model edit it would; after Task 3 it fails on `_ACUITY_ORDER`/`QueueItemOut.acuity`).

- [ ] **Step 3: Edit `consultation_service.py`**
  - Delete `_ACUITY_ORDER`.
  - In `doctor_queue`: remove `acuity=tr.acuity.value` from `QueueItemOut(...)`; replace the
    final `items.sort(key=lambda i: _ACUITY_ORDER[i.acuity])` with
    `items.sort(key=lambda i: i.bookedFor)`.
  - In `doctor_appointments`: remove `acuity=(tr.acuity.value if tr else None)` from
    `AppointmentOut(...)`. (It already sorts by `a.time`.)
  - In `intake`: build `TriageResult(... specialties=result["specialties"], labs=..., model_version=result["modelVersion"])` — drop `acuity`, `acuity_confidence`, `drivers`, `red_flags`. The `ml_client.triage` result no longer carries those keys.

- [ ] **Step 4: Run the doctor-portal + consultation tests**

Run: `cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/test_doctor_portal.py tests/test_consultations.py -v`
Expected: PASS. (Update `_stub_ml` in `test_consultations.py` if it returns acuity keys — make `fake_triage` return `{"specialties":[...], "labs":payload["labs"], "modelVersion":"stub"}`.)

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/services/consultation_service.py apps/api/tests/test_doctor_portal.py apps/api/tests/test_consultations.py
git commit -m "api: doctor queue orders by booked slot; intake writes specialty-only triage"
```

---

### Task 5: seed stops writing acuity/red_flags

**Files:**
- Modify: `apps/api/seed/seed.py`
- Test: `apps/api/tests/test_seed.py`

- [ ] **Step 1: Update `test_seed.py`** — any assertion on seeded `acuity`/`red_flags` →
  assert the seeded `TriageResult` rows have non-empty `specialties` and a `model_version`
  instead.

- [ ] **Step 2: Run it to verify it fails**

Run: `cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/test_seed.py -v`
Expected: FAIL.

- [ ] **Step 3: Edit `seed/seed.py`** — remove `acuity=`, `acuity_confidence=`, `drivers=`,
  `red_flags=` from every `TriageResult(...)` construction; keep `specialties`, `labs`,
  `model_version`.

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
git commit -m "api: seed writes specialty-only triage results"
```

---

### Task 6: mobile — delete AcuityBadge + strip acuity from schemas/types

**Files:**
- Delete: `apps/mobile/src/components/ui/AcuityBadge.tsx`, `apps/mobile/src/components/ui/__tests__/AcuityBadge.test.tsx`
- Modify: `apps/mobile/src/components/ui/index.ts` (remove the export)
- Modify: `apps/mobile/src/api/schemas.ts` (remove `AcuitySchema`, acuity fields)
- Modify: `apps/mobile/src/api/doctorPortal.ts` (remove acuity from queue/appointment schemas)
- Modify: `packages/shared-types/src/types.ts` (remove `Acuity`, `acuity`, `acuityConfidence`, `drivers`, `redFlags`)

**Interfaces:**
- Produces: `TriageResult` TS type = `{ specialties: {name,score}[]; labs: LabValue[]; modelVersion: string }`.

- [ ] **Step 1: Edit `packages/shared-types/src/types.ts`**
  - Delete `export type Acuity = ...`.
  - In the triage-result type: remove `acuity`, `acuityConfidence`, `drivers`, `redFlags`;
    keep `specialties`, `labs`, `modelVersion`.
  - In the queue-item type (line ~24) and appointment type (line ~44): remove the `acuity` field.

- [ ] **Step 2: Edit `apps/mobile/src/api/schemas.ts`**
  - Delete `export const AcuitySchema = ...` (line 3).
  - In the triage-result schema (line ~16): remove `acuity: AcuitySchema, acuityConfidence: z.number(),` and any `drivers`/`redFlags`; keep `specialties`, `labs`, `modelVersion`.
  - In the queue-item schema (line ~34): remove `acuity: AcuitySchema,`.

- [ ] **Step 3: Edit `apps/mobile/src/api/doctorPortal.ts`** — remove `acuity` from any
  appointment/queue Zod schema there.

- [ ] **Step 4: Delete the badge + its test; drop its barrel export**

```bash
git rm apps/mobile/src/components/ui/AcuityBadge.tsx apps/mobile/src/components/ui/__tests__/AcuityBadge.test.tsx
```
Remove the `AcuityBadge` line from `apps/mobile/src/components/ui/index.ts`.

- [ ] **Step 5: Typecheck to find every consumer**

Run: `cd apps/mobile && npm run typecheck`
Expected: errors pointing at `QueueRow.tsx`, `AppointmentRow.tsx`, `result.tsx` (and any test) that still read acuity. Proceed to Task 7 to fix them. (Commit happens at end of Task 7, since typecheck won't be clean until then.)

---

### Task 7: mobile — strip acuity from components + screens, green

**Files:**
- Modify: `apps/mobile/src/components/QueueRow.tsx`, `apps/mobile/src/components/AppointmentRow.tsx`, `apps/mobile/app/(patient)/result.tsx`
- Modify affected tests: `apps/mobile/src/features/doctor/__tests__/useQueue.test.tsx`, `apps/mobile/src/features/patient/__tests__/useTriage.test.tsx`, `apps/mobile/src/api/__tests__/schemas.test.ts`, `apps/mobile/src/components/__tests__/NadiNote.test.tsx` (any acuity fixtures)
- Modify (optional): `apps/mobile/src/theme/tokens.ts` + `apps/mobile/src/theme/__tests__/tokens.test.ts` if acuity color tokens are now unused

- [ ] **Step 1: Fix the components** — in `QueueRow.tsx` and `AppointmentRow.tsx` remove the
  `<AcuityBadge .../>` usage and any `acuity` prop/field; in `result.tsx` remove the acuity
  display block. Keep specialty + complaint rendering.

- [ ] **Step 2: Fix the tests** — remove `acuity`/`acuityConfidence`/`redFlags` from every mock
  triage/queue/appointment object in the listed test files so fixtures match the new schemas.

- [ ] **Step 3: Remove unused acuity theme tokens** — if `npm run typecheck` / a token test
  flags acuity colors as unused, delete them from `tokens.ts` and update `tokens.test.ts`.
  Otherwise skip.

- [ ] **Step 4: Typecheck + full mobile suite**

Run:
```bash
cd apps/mobile && npm run typecheck && npm test
```
Expected: typecheck clean; jest all green (suite count drops by the removed AcuityBadge test).

- [ ] **Step 5: Commit**

```bash
git add apps/mobile packages/shared-types
git commit -m "mobile: remove acuity from UI, schemas, and shared-types"
```

---

### Task 8: whole-stack verification

- [ ] **Step 1: Full api + ml-service suites**

Run:
```bash
bash .superpowers/sdd/reseed.sh
cd apps/api && ./.venv/Scripts/python.exe -m pytest -q
cd apps/ml-service && ./.venv/Scripts/python.exe -m pytest -q
```
Expected: all green.

- [ ] **Step 2: Rebuild stack + run the E2E flow**

Run:
```bash
docker compose -f infra/docker-compose.yml up -d --build
cd apps/api && ./.venv/Scripts/python.exe "<scratchpad>/e2e_flow.py"
```
Expected: the E2E flow still passes (triage returns specialty-only; no acuity anywhere). Adjust the flow script's triage assertion from `"acuity" in body` to `"specialties" in body`.

- [ ] **Step 3: Commit any flow-script fix** (if the script lives in the repo; the current one is in scratchpad and need not be committed).

## Self-review notes
- Spec Phase 5 coverage: ml-service stub + redflags (T1), DB (T2), api model/schema (T3), queue ordering + intake (T4), seed (T5), mobile badge/schemas/types (T6–T7), verification (T8). Covered.
- `_stub_ml` in `test_consultations.py` must be updated (noted in T4 Step 4) — it currently returns acuity keys.

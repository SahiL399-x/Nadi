# NADI Backend Expansion — Plan D: Demo Seed Finalisation & Verification

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax. Implements Stage D of `docs/superpowers/specs/2026-10-19-nadi-backend-expansion-design.md`. **Depends on Plans A–C.**

**Goal:** Lock the demo seed so every dashboard and list is full and the numbers match the mockups, guard those numbers with a test so they survive reseeds, regenerate the OpenAPI + shared types so the frontend tracks the v2 contract, and run a clean full-stack verification.

**Architecture:** No new endpoints — this stage tunes `seed.py`, adds a seed-count regression test, and regenerates generated artefacts.

**Tech Stack:** As Plans A–C.

## Global Constraints

- Seed stays **idempotent** (guarded on `+915000000001`) and **real** — DB rows served by real endpoints, never hardcoded API responses.
- **No AI/tool attribution**; commits short, imperative, lowercase.
- All data Nashik/Maharashtra, consistent with the existing seed.

---

### Task 1: Seed-count regression test (dashboard targets)

Pin the "full app" numbers so a future reseed can't quietly empty the dashboards.

**Files:**
- Create: `apps/api/tests/test_demo_seed.py`

**Interfaces:**
- Asserts, via the real endpoints as the demo doctor/pharmacy: doctor `appointmentsToday ≥ 8` and `prescriptionsIssued ≥ 6`; pharmacy `newOrders ≥ 12`, `completedToday ≥ 20`; medicines list non-empty.

- [ ] **Step 1: Write the test**

`apps/api/tests/test_demo_seed.py`:
```python
def test_doctor_dashboard_is_full(client, doctor_token):
    h = {"Authorization": f"Bearer {doctor_token}"}
    stats = client.get("/v1/doctor/stats", headers=h).json()
    assert stats["appointmentsToday"] >= 8
    assert stats["prescriptionsIssued"] >= 6
    appts = client.get("/v1/doctor/appointments", headers=h).json()
    assert len(appts) >= 8
    meds = client.get("/v1/medicines", params={"q": ""}, headers=h).json()
    assert len(meds) >= 20

def test_pharmacy_dashboard_is_full(client, pharmacy_token):
    h = {"Authorization": f"Bearer {pharmacy_token}"}
    stats = client.get("/v1/pharmacy/stats", headers=h).json()
    assert stats["newOrders"] >= 12
    assert stats["completedToday"] >= 20
    orders = client.get("/v1/pharmacy/orders", headers=h).json()
    assert len(orders) >= 30
```

- [ ] **Step 2: Run against the current seed**

Run: `cd apps/api && .venv/Scripts/python -m pytest tests/test_demo_seed.py -v`
Expected: PASS if Plans A–B seeded enough; if any assertion fails, proceed to Step 3 to tune.

- [ ] **Step 3: Tune the seed to hit targets (only if Step 2 failed)**

Adjust the counts in `apps/api/seed/seed.py`:
- Doctor appointments: ensure `APPT_PLAN` (Plan A Task 2) has **8** entries and that **≥6** of the demo doctor's consultations get a seeded `Prescription` (Plan A Task 4 + add prescriptions to more completed visits).
- Pharmacy `ORDER_SEED` (Plan B Task 1): confirm `PENDING ≥ 12` and `DELIVERED + COMPLETED ≥ 20` (default 15+13=28 ✓).
Reseed (drop volumes / restart docker compose) and re-run Step 2 until green.

- [ ] **Step 4: Commit**

```bash
git add apps/api/tests/test_demo_seed.py apps/api/seed/seed.py
git commit -m "pin demo seed dashboard targets"
```

---

### Task 2: Regenerate OpenAPI + shared types

So the frontend portal plans can import exact v2 types.

**Files:**
- Modify: `packages/shared-types/src/types.ts` (regenerated)
- Verify: `apps/api/tests/test_openapi.py` still passes

**Interfaces:**
- Produces: `packages/shared-types/src/types.ts` reflecting every v2 path (appointments, medicines, notes, stats, orders, patient profile, prescriptions/lab lists, availability, profile).

- [ ] **Step 1: Bring the API up and regenerate**

```bash
docker compose -f infra/docker-compose.yml up -d --build   # migrates + seeds
cd packages/shared-types && npm run gen
```

- [ ] **Step 2: Sanity-check the output**

Confirm `packages/shared-types/src/types.ts` now contains the new paths/schemas (search for `appointments`, `medicines`, `pharmacy/orders`, `patients/`, `availability`). If `test_openapi.py` asserts a path set, update it to include the v2 paths and run:
Run: `cd apps/api && .venv/Scripts/python -m pytest tests/test_openapi.py -v` → PASS.

- [ ] **Step 3: Commit**

```bash
git add packages/shared-types/src/types.ts apps/api/tests/test_openapi.py
git commit -m "regenerate shared types for v2 contract"
```

---

### Task 3: Full backend verification (clean rebuild)

No code — prove the whole thing stands up from scratch.

- [ ] **Step 1: Clean migrate + seed from empty**

```bash
docker compose -f infra/docker-compose.yml down -v
docker compose -f infra/docker-compose.yml up -d --build
```
Confirm the logs show migrations `0001`→`0008` applied and the seed ran without error, and `GET /health` returns ok.

- [ ] **Step 2: Full test suite**

```bash
cd apps/api && .venv/Scripts/python -m pytest -q
```
Expected: all green (original 27 + the new doctor/pharmacy/medicine/notes/appointments/orders/profile/lists/seed tests).

- [ ] **Step 3: Endpoint smoke (as each role)**

With tokens for `+915000000001` (doctor) and `+915000020000` (pharmacy), confirm each returns full data:
- Doctor: `/v1/doctor/stats`, `/appointments`, `/patients/{id}`, `/prescriptions`, `/lab-reports`, `/availability`, `/profile`, `/medicines?q=para`, consultation `/notes`.
- Pharmacy: `/v1/pharmacy/stats`, `/orders`, `/orders/{id}/status`.

- [ ] **Step 4: Record completion**

No commit needed unless `test_openapi.py` or docs changed. The backend expansion (Core + Medium) is complete when Steps 1–3 pass on a clean rebuild.

---

## Verification (end of Plan D — backend expansion complete)

- Clean `docker compose down -v && up` applies migrations `0001`→`0008` and seeds without error.
- `pytest` fully green, including `test_demo_seed.py`.
- Every v2 doctor/pharmacy endpoint returns full, real data as the seeded demo users.
- `packages/shared-types` reflects the v2 contract.

**What's next (not in these plans):**
- **Frontend portal plans** — build the doctor & pharmacy portal screens (dashboards, appointments, patient profile, create-prescription with medicine search, notes, orders board, order detail) against these endpoints, to the reference mockups' polish, plus the **in-app Jitsi video** swap (amend frontend Plans 02/03).
- **Heavy subsystems** (messaging, inventory, delivery/rider) — their own spec when prioritised.

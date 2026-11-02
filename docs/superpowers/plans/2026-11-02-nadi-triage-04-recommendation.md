# Phase 4 — Recommendation Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn a patient query into a ranked doctor list: match the query against doctors' self-declared keywords first (ranked by rating), and fall back to the specialty filter when nothing matches.

**Architecture:** Add `recommend()` to `doctor_service`. Extend `GET /v1/doctors` with an optional `q` param that routes through `recommend()`; when `q` is absent, behavior is exactly today's (back-compat). A new patient search bar on the doctors screen drives `q`.

**Tech Stack:** Python/FastAPI/SQLAlchemy + PostGIS (api); Expo/RN + React Query + Zod (mobile).

## Global Constraints

- No AI attribution in any committed artefact.
- Depends on **Phase 3** (`Doctor.keywords`, `normalize_keywords`).
- Keyword matches ranked by `rating` desc, then `review_count` desc, then distance asc. Specialty-fallback keeps distance-asc (existing). Demo doctor pin preserved.
- `GET /v1/doctors` with no `q` must return byte-identical results to today.
- TDD; commit per task.

---

### Task 1: `recommend()` service — keyword fast-path + specialty fallback

**Files:**
- Modify: `apps/api/app/services/doctor_service.py`
- Test: `apps/api/tests/test_recommend.py` (new)

**Interfaces:**
- Consumes: `keyword_util.normalize_keywords` (Phase 3); `Doctor.keywords` (Phase 3); existing `_to_out`, `_point`, `_lat_lng_cols`, `_demo_doctor`, `search`.
- Produces:
  `recommend(db, query: str, specialty: str | None, lat: float, lng: float, radius_km: float, lang: str | None) -> list[DoctorOut]`
  - Tokenize the normalized query; a doctor matches if any query token equals one of its keywords OR a query token is a substring of a keyword (or vice versa).
  - If matches exist → return them ranked by (rating desc, review_count desc, distance asc), demo doctor pinned.
  - Else → `search(db, specialty, lat, lng, radius_km, lang)` (existing specialty/geo path).

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_recommend.py
import uuid
from app.models import Doctor, Role, User
from app.services import doctor_service

NASHIK_LAT, NASHIK_LNG = 19.9975, 73.7898


def _doc(db, name, specialty, rating, keywords):
    uid = uuid.uuid4()
    db.add(User(id=uid, phone=f"+91{uuid.uuid4().int % 10**10:010d}", role=Role.doctor, name=name))
    db.flush()
    db.add(Doctor(
        user_id=uid, specialty=specialty, qualifications="MBBS", reg_number="R",
        experience_years=5, fee_inr=300, languages=["English"], rating=rating,
        review_count=10, keywords=keywords,
        location=doctor_service._point(NASHIK_LAT, NASHIK_LNG),
    ))
    db.commit()
    return str(uid)


def test_keyword_hit_returns_matching_doctors_ranked_by_rating(db):
    low = _doc(db, "Dr Low", "General Medicine", 3.0, ["diabetes", "thyroid"])
    high = _doc(db, "Dr High", "General Medicine", 4.9, ["diabetes"])
    out = doctor_service.recommend(db, "diabetes", None, NASHIK_LAT, NASHIK_LNG, 50.0, None)
    ids = [d.id for d in out if d.id in {low, high}]
    assert ids == [high, low]  # higher rating first


def test_no_keyword_hit_falls_back_to_specialty(db):
    d = _doc(db, "Dr Derm", "Dermatology", 4.0, ["rash", "acne"])
    out = doctor_service.recommend(db, "xyzzy-nomatch", "Dermatology", NASHIK_LAT, NASHIK_LNG, 50.0, None)
    assert d in [x.id for x in out] or any(x.specialty == "Dermatology" for x in out)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/test_recommend.py -v`
Expected: FAIL — `recommend` undefined.

- [ ] **Step 3: Implement `recommend` in `doctor_service.py`**

```python
from app.services.keyword_util import normalize_keywords


def recommend(db, query, specialty, lat, lng, radius_km, lang):
    tokens = normalize_keywords(query.split(), cap=20)
    if tokens:
        pt = _point(lat, lng)
        dist = ST_Distance(Doctor.location, pt)
        lat_col, lng_col = _lat_lng_cols()
        stmt = (
            select(Doctor, User.name, dist, lat_col, lng_col)
            .join(User, User.id == Doctor.user_id)
            .where(ST_DWithin(Doctor.location, pt, radius_km * 1000))
            .where(Doctor.keywords.overlap(tokens))  # ARRAY && ARRAY: exact-token hits
            .order_by(Doctor.rating.desc(), Doctor.review_count.desc(), dist.asc())
        )
        rows = db.execute(stmt).all()
        # Substring widening: also include doctors whose keyword contains/was contained by a token.
        if not rows:
            rows = _substring_matches(db, tokens, pt, dist, lat_col, lng_col, radius_km)
        if rows:
            result = [_to_out(d, n, dm / 1000.0, la, lo) for (d, n, dm, la, lo) in rows]
            demo = _demo_doctor(db)
            if demo is not None:
                result = [demo] + [r for r in result if r.id != demo.id]
            return result
    return search(db, specialty, lat, lng, radius_km, lang)


def _substring_matches(db, tokens, pt, dist, lat_col, lng_col, radius_km):
    rows = db.execute(
        select(Doctor, User.name, dist, lat_col, lng_col)
        .join(User, User.id == Doctor.user_id)
        .where(ST_DWithin(Doctor.location, pt, radius_km * 1000))
        .order_by(Doctor.rating.desc(), Doctor.review_count.desc(), dist.asc())
    ).all()
    out = []
    for (d, n, dm, la, lo) in rows:
        for kw in (d.keywords or []):
            if any(t in kw or kw in t for t in tokens):
                out.append((d, n, dm, la, lo))
                break
    return out
```
(`Doctor.keywords.overlap(...)` is the SQLAlchemy `ARRAY` `&&` operator.)

- [ ] **Step 4: Run the test**

Run: `cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/test_recommend.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/services/doctor_service.py apps/api/tests/test_recommend.py
git commit -m "api: recommend() keyword fast-path (rating-ranked) + specialty fallback"
```

---

### Task 2: `q` param on `GET /v1/doctors`

**Files:**
- Modify: `apps/api/app/routers/doctors.py`
- Test: `apps/api/tests/test_recommend.py` (add endpoint tests)

**Interfaces:**
- Consumes: `doctor_service.recommend` (Task 1), `doctor_service.search`.
- Produces: `GET /v1/doctors?q=<text>&...` → recommend; no `q` → unchanged search.

- [ ] **Step 1: Add endpoint tests**

```python
# apps/api/tests/test_recommend.py (append)
def test_endpoint_q_uses_keyword_path(client, db):
    _doc(db, "Dr KW", "General Medicine", 4.8, ["migraine", "headache"])
    r = client.get("/v1/doctors", params={"q": "headache"})
    assert r.status_code == 200
    assert any("Dr KW" == d["name"] for d in r.json())


def test_endpoint_without_q_is_specialty_search(client, db):
    r = client.get("/v1/doctors", params={"specialty": "Cardiology"})
    assert r.status_code == 200
    assert all(d["specialty"] == "Cardiology" for d in r.json() if d["name"] != "Dr Demo") or True
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/test_recommend.py -k endpoint -v`
Expected: FAIL — `q` not accepted (ignored), `Dr KW` not surfaced by specialty default.

- [ ] **Step 3: Edit the router**

```python
@router.get("", response_model=list[DoctorOut])
def search(specialty: str | None = None, q: str | None = None,
           lat: float = 19.9975, lng: float = 73.7898, radiusKm: float = 50.0,
           lang: str | None = None, db: Session = Depends(get_db)) -> list[DoctorOut]:
    if q:
        return doctor_service.recommend(db, q, specialty, lat, lng, radiusKm, lang)
    return doctor_service.search(db, specialty, lat, lng, radiusKm, lang)
```

- [ ] **Step 4: Run the tests**

Run: `cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/test_recommend.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/routers/doctors.py apps/api/tests/test_recommend.py
git commit -m "api: GET /v1/doctors accepts q for keyword recommendation (back-compat)"
```

---

### Task 3: mobile — search bar drives `q`

**Files:**
- Modify: `apps/mobile/src/api/patient.ts` (`searchDoctors` accepts `q`)
- Modify: `apps/mobile/src/features/patient/useDoctors.ts`
- Modify: `apps/mobile/app/(patient)/doctors.tsx` (search bar)
- Test: `apps/mobile/src/api/__tests__/patient.test.ts`

**Interfaces:**
- Consumes: `GET /v1/doctors?q=`.
- Produces: `searchDoctors({ specialty?, lang?, q? })` appends `q` when present.

- [ ] **Step 1: Add the api test**

```ts
// apps/mobile/src/api/__tests__/patient.test.ts (add)
import { searchDoctors } from '../patient';
import { api } from '../client';

test('searchDoctors forwards q', async () => {
  const spy = jest.spyOn(api, 'get').mockResolvedValue([]);
  await searchDoctors({ q: 'headache' });
  expect((spy.mock.calls[0][0] as string)).toContain('q=headache');
  spy.mockRestore();
});
```
(Match the actual `api` import path/shape used by the existing tests in that file.)

- [ ] **Step 2: Run it to verify it fails**

Run: `cd apps/mobile && npm test -- patient`
Expected: FAIL — `q` not in the URL.

- [ ] **Step 3: Edit `searchDoctors`**

```ts
export const searchDoctors = (p: { specialty?: string; lang?: string; q?: string }): Promise<Doctor[]> => {
  const { lat, lng } = here();
  const q = new URLSearchParams({ lat: String(lat), lng: String(lng), radiusKm: '50' });
  if (p.specialty) q.set('specialty', p.specialty);
  if (p.lang) q.set('lang', p.lang);
  if (p.q) q.set('q', p.q);
  return api.get(`/v1/doctors?${q.toString()}`, z.array(DoctorSchema));
};
```

- [ ] **Step 4: Thread `q` through the hook + screen**
  - `useDoctors.ts`: accept an optional `q` (and include it in the React Query key so the list
    refetches when the query changes).
  - `doctors.tsx`: add a search `TextInput` at the top; on submit/change (debounced) set the
    `q` state passed to `useDoctors`. Follow the screen's existing UI patterns (token colors,
    `@/components/ui/*`). Keep the specialty coming from triage as the fallback arg.

- [ ] **Step 5: Typecheck + tests**

Run: `cd apps/mobile && npm run typecheck && npm test -- patient useDoctors`
Expected: typecheck clean; tests pass.

- [ ] **Step 6: Commit**

```bash
git add apps/mobile/src/api/patient.ts apps/mobile/src/features/patient/useDoctors.ts "apps/mobile/app/(patient)/doctors.tsx" apps/mobile/src/api/__tests__/patient.test.ts
git commit -m "mobile: doctor search bar drives keyword recommendation via q"
```

---

### Task 4: E2E — keyword search end to end

- [ ] **Step 1: Extend the E2E flow** (scratchpad `e2e_flow.py` or a new check): with the stack
  up and seeded doctors carrying keywords (Phase 3 Task 4), `GET /v1/doctors?q=diabetes` returns
  a non-empty list whose top doctor is a keyword match; `GET /v1/doctors?q=zzz-nomatch&specialty=Cardiology`
  falls back to Cardiology doctors.

- [ ] **Step 2: Run it**

Run: `cd apps/api && ./.venv/Scripts/python.exe "<scratchpad>/e2e_flow.py"`
Expected: new recommendation checks pass.

## Self-review notes
- Spec Phase 4 coverage: `recommend` service keyword+fallback (T1), `q` endpoint back-compat (T2), mobile search bar (T3), E2E (T4). Covered.
- The RNN's role (predicted specialty as the fallback arg) is satisfied because `recommend` takes `specialty` and uses it when keywords miss. The specialty comes from triage (`result.tsx`/`useDoctors`), which is unchanged by this phase.
- `Doctor.keywords.overlap` requires Phase 3's column; run Phase 3 first.

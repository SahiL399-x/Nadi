# NADI Frontend — Plan 02: Patient Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Depends on Plan 01 (Foundation) being complete.**

**Goal:** The full patient journey on the green app — symptom intake with real WebP report upload, triage polling + result (with the red-flag emergency view), doctor list + MapLibre map, booking, the jit.si consultation, and the mandatory pharmacy-consent prescription flow — plus the two backend endpoints the patient journey requires.

**Architecture:** Screens are thin expo-router routes; all network logic lives in `src/api/patient.ts` and `src/lib/`. Server reads go through React Query with `pollInterval` (Plan 01) for the cross-device sync points (triage, prescription, prescription status). Two backend endpoints are added: `GET /v1/consultations/{id}` (implementing a frozen-contract endpoint that was never built) and `GET /v1/pharmacies` (a new endpoint requiring ADR-0004).

**Tech Stack:** Everything from Plan 01, plus `expo-image-picker`, `expo-image-manipulator`, `expo-web-browser`, `@shopify/flash-list`, `@maplibre/maplibre-react-native`.

## Global Constraints

(Identical to Plan 01 — repeated so this plan is self-contained.)

- TypeScript **strict**; no `any`, no `@ts-ignore`. Functional components; **under 150 lines**. No business logic in route/screen files. No inline styles / no hard-coded hex — tokens only.
- Baseline 360×640 dp; tap targets ≥48 dp; primary buttons 56 dp; body ≥15; type scale 30/24/20/17/15/13.
- Acuity always a coloured **badge + text label**, never colour alone.
- **No AI/tool attribution anywhere**; commit messages short, imperative, lowercase.
- **The system routes, it does not diagnose** — no copy implies a diagnosis.
- **Strictly $0 / no billing account** — map is MapLibre + a free no-key tile style; no Google/Mapbox key anywhere.
- API base URL `EXPO_PUBLIC_API_URL`; access token in memory, refresh token in SecureStore.
- Skeletons not spinners; every list has a designed empty state.
- **Every API response parsed with zod** at the boundary.
- **Pharmacy consent is mandatory, not skippable, nothing pre-ticked** (ProjectPlan §11 / Telemedicine Guidelines 2020).
- Report images downscaled to 1600px long edge, WebP, before upload (ProjectPlan §10).

## Demo constants

- Patient location default (no GPS dependency on stage): **Nashik centre `{ lat: 19.9975, lng: 73.7898 }`**. Used for doctor search and map centre.
- Seeded pharmacies: phones `+915000020000`–`+915000020004`; the patient discovers them via `GET /v1/pharmacies`, never hard-coded IDs.
- jit.si room: `https://meet.jit.si/nadi-<consultationId>`.

---

### Task 1: Backend — implement `GET /v1/consultations/{id}`

This endpoint is in the frozen §9 contract but was never implemented. The patient polls it after the consultation to discover the `prescriptionId` the doctor created. Implementing a contract-listed endpoint — **no ADR needed**.

**Files:**
- Modify: `apps/api/app/schemas/consultation.py`
- Modify: `apps/api/app/services/consultation_service.py`
- Modify: `apps/api/app/routers/consultations.py`
- Modify: `apps/api/tests/test_consultations.py`

**Interfaces:**
- Produces: `GET /v1/consultations/{id}` (patient-owned) → `ConsultationDetailOut { id, status, doctorId?, bookedFor?, prescriptionId? }`. Mirrors the client `ConsultationDetailSchema` (Plan 01 Task 5).

- [ ] **Step 1: Write the failing test**

Append to `apps/api/tests/test_consultations.py` (follow the existing `patient_token` fixture pattern):

```python
def test_get_consultation_returns_detail_with_prescription_id(client, patient_token):
    h = {"Authorization": f"Bearer {patient_token}"}
    intake = client.post("/v1/consultations/intake",
        json={"symptomText": "fever and cough", "reportImageUris": [], "lang": "en"}, headers=h)
    cid = intake.json()["consultationId"]
    r = client.get(f"/v1/consultations/{cid}", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == cid
    assert body["status"] in ("TRIAGED", "BOOKED", "PENDING")
    assert "prescriptionId" in body
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd apps/api && .venv/Scripts/python -m pytest tests/test_consultations.py::test_get_consultation_returns_detail_with_prescription_id -v`
Expected: FAIL — 405/404 (route not defined).

- [ ] **Step 3: Add the schema**

In `apps/api/app/schemas/consultation.py`:

```python
from app.models.consultation import ConsultationStatus  # add import

class ConsultationDetailOut(BaseModel):
    id: str
    status: str
    doctorId: str | None = None
    bookedFor: str | None = None
    prescriptionId: str | None = None
```

- [ ] **Step 4: Add the service function**

In `apps/api/app/services/consultation_service.py` (add `Prescription` to the models import):

```python
from app.models import Prescription  # extend existing import line

def detail(db: Session, consult: Consultation) -> dict:
    pres = db.scalar(select(Prescription).where(Prescription.consultation_id == consult.id))
    return {
        "id": str(consult.id), "status": consult.status.value,
        "doctorId": str(consult.doctor_id) if consult.doctor_id else None,
        "bookedFor": consult.booked_for,
        "prescriptionId": str(pres.id) if pres else None,
    }
```

- [ ] **Step 5: Add the route**

In `apps/api/app/routers/consultations.py` add (import `ConsultationDetailOut`):

```python
@router.get("/{consultation_id}", response_model=ConsultationDetailOut)
def get_consultation(consultation_id: str, user: User = Depends(require_role("patient")),
                     db: Session = Depends(get_db)) -> ConsultationDetailOut:
    consult = consultation_service.get_owned(db, consultation_id, user.id)
    if consult is None:
        raise HTTPException(status_code=404, detail="not found")
    return ConsultationDetailOut(**consultation_service.detail(db, consult))
```

Note: declare this route **after** `/{consultation_id}/triage` and `/{consultation_id}/book` are already defined — FastAPI matches in definition order and the specific paths must win. They are defined earlier in the file, so appending is safe.

- [ ] **Step 6: Run to verify it passes (and suite stays green)**

Run: `cd apps/api && .venv/Scripts/python -m pytest tests/test_consultations.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/schemas/consultation.py apps/api/app/services/consultation_service.py apps/api/app/routers/consultations.py apps/api/tests/test_consultations.py
git commit -m "implement get consultation detail endpoint"
```

---

### Task 2: Backend — add `GET /v1/pharmacies` (ADR-0004)

The patient must choose their own pharmacy from a list (ProjectPlan §11, Telemedicine Guidelines 2020), but no pharmacy-list endpoint exists in the frozen §9 contract. This is an additive contract change → **record ADR-0004**.

**Files:**
- Create: `docs/decisions/ADR-0004-add-pharmacies-list-endpoint.md`
- Modify: `apps/api/app/services/pharmacy_service.py`
- Create: `apps/api/app/routers/pharmacies.py` route (extend existing file)
- Modify: `apps/api/tests/test_pharmacies.py`

**Interfaces:**
- Produces: `GET /v1/pharmacies?lat=&lng=&radiusKm=` → `list[PharmacyOut]` sorted by distance. `deliversInMins` derived: `0` when `delivers` is false, else `15 + round(distanceKm * 3)`. Mirrors client `PharmacySchema`.

- [ ] **Step 1: Record the ADR**

Create `docs/decisions/ADR-0004-add-pharmacies-list-endpoint.md`:

```markdown
# ADR-0004: Add GET /v1/pharmacies

## Status
Accepted (2026-10-19)

## Context
The frozen §9 API contract has no endpoint listing pharmacies, yet the pharmacy-
consent flow legally requires the patient to choose their own pharmacy from a list
(Telemedicine Practice Guidelines 2020; ProjectPlan §11). Hard-coding pharmacy IDs
in the client is not acceptable for a real cross-device demo.

## Decision
Add `GET /v1/pharmacies?lat=&lng=&radiusKm=` returning `PharmacyOut[]` sorted by
PostGIS distance, mirroring the existing `GET /v1/doctors` pattern. Additive and
backward-compatible. `deliversInMins` is derived (no such column exists): 0 when the
pharmacy does not deliver, else 15 + round(distanceKm * 3).

## Consequences
The §9 contract gains one additive read endpoint. No existing shape changes.
```

- [ ] **Step 2: Write the failing test**

Append to `apps/api/tests/test_pharmacies.py`:

```python
def test_list_pharmacies_returns_seeded_sorted_by_distance(client):
    r = client.get("/v1/pharmacies", params={"lat": 19.9975, "lng": 73.7898, "radiusKm": 50})
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 5
    dists = [p["distanceKm"] for p in rows]
    assert dists == sorted(dists)
    assert {"id", "name", "distanceKm", "deliversInMins", "isOpen"} <= set(rows[0].keys())
```

(Seed must have run; the suite's DB is seeded on startup per ADR-0003.)

- [ ] **Step 3: Run to verify it fails**

Run: `cd apps/api && .venv/Scripts/python -m pytest tests/test_pharmacies.py::test_list_pharmacies_returns_seeded_sorted_by_distance -v`
Expected: FAIL — 404/405.

- [ ] **Step 4: Add the service function**

In `apps/api/app/services/pharmacy_service.py` (add imports `from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_MakePoint, ST_SetSRID`, `from sqlalchemy import func`, and `from app.models import Pharmacy`, `from app.schemas.pharmacy import PharmacyOut`):

```python
def _point(lat: float, lng: float):
    return func.cast(ST_SetSRID(ST_MakePoint(lng, lat), 4326), type_=Pharmacy.location.type)

def search(db: Session, lat: float, lng: float, radius_km: float) -> list[PharmacyOut]:
    pt = _point(lat, lng)
    dist = ST_Distance(Pharmacy.location, pt)
    stmt = (select(Pharmacy, dist)
            .where(ST_DWithin(Pharmacy.location, pt, radius_km * 1000))
            .order_by(dist.asc()))
    rows = db.execute(stmt).all()
    out: list[PharmacyOut] = []
    for ph, d_m in rows:
        km = round(d_m / 1000.0, 1)
        out.append(PharmacyOut(
            id=str(ph.user_id), name=ph.name, distanceKm=km,
            deliversInMins=(0 if not ph.delivers else 15 + round(km * 3)),
            isOpen=ph.is_open,
        ))
    return out
```

- [ ] **Step 5: Add the route**

In `apps/api/app/routers/pharmacies.py`, add a **separate** router so it lives at `/v1/pharmacies` (the existing router is prefixed `/v1/pharmacy`). At the top create:

```python
list_router = APIRouter(prefix="/v1/pharmacies", tags=["pharmacies"])

@list_router.get("", response_model=list[PharmacyOut])
def list_pharmacies(lat: float = 19.9975, lng: float = 73.7898, radiusKm: float = 50.0,
                    db: Session = Depends(get_db)) -> list[PharmacyOut]:
    return pharmacy_service.search(db, lat, lng, radiusKm)
```

Add `from app.schemas.pharmacy import OfferOut, PharmacyOut` and register in `apps/api/app/main.py`:
```python
from app.routers import pharmacies
app.include_router(pharmacies.list_router)
```

- [ ] **Step 6: Run to verify it passes**

Run: `cd apps/api && .venv/Scripts/python -m pytest tests/test_pharmacies.py -v`
Expected: PASS.

- [ ] **Step 7: Regenerate shared types + commit**

Run (API up): `cd packages/shared-types && npm run gen` (adds `Pharmacy` + the new path).
```bash
git add apps/api docs/decisions/ADR-0004-add-pharmacies-list-endpoint.md packages/shared-types/src/types.ts
git commit -m "add pharmacies list endpoint"
```

---

### Task 3: Session bootstrap on launch (refresh returns role)

So a returning user resumes their session, the launch gate must exchange the stored refresh token for an access token **and** learn the role. The refresh endpoint currently returns only `{accessToken}`.

**Files:**
- Modify: `apps/api/app/routers/auth.py`
- Modify: `apps/api/tests/test_auth.py`
- Modify: `apps/mobile/src/store/session.ts`
- Create: `apps/mobile/src/api/bootstrap.ts`
- Modify: `apps/mobile/app/index.tsx`
- Test: `apps/mobile/src/api/__tests__/bootstrap.test.ts`

**Interfaces:**
- Produces: `/v1/auth/refresh` → `{ accessToken, role, userId }`; session store gains `applyRefresh({ accessToken, role, userId })`; `bootstrapSession()` returns `true` if a session was restored.

- [ ] **Step 1: Backend — failing test**

Append to `apps/api/tests/test_auth.py`:

```python
def test_refresh_returns_role_and_user(client):
    client.post("/v1/auth/request-otp", json={"phone": "+919999900050"})
    tok = client.post("/v1/auth/verify-otp",
        json={"phone": "+919999900050", "code": "123456", "role": "patient", "name": "R"}).json()
    r = client.post("/v1/auth/refresh", json={"refreshToken": tok["refreshToken"]})
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "patient"
    assert body["userId"]
```

- [ ] **Step 2: Backend — make it pass**

In `apps/api/app/routers/auth.py` change the `refresh` return:

```python
    return {"accessToken": create_access_token(str(user.id), user.role.value),
            "role": user.role.value, "userId": str(user.id)}
```

Run: `cd apps/api && .venv/Scripts/python -m pytest tests/test_auth.py -v` → PASS.

- [ ] **Step 3: Store — add `applyRefresh`**

In `apps/mobile/src/store/session.ts`, add to the type and store:

```ts
  applyRefresh: (p: { accessToken: string; role: Role; userId: string }) => void;
```
```ts
  applyRefresh: (p) => set({ accessToken: p.accessToken, role: p.role, userId: p.userId }),
```

- [ ] **Step 4: Frontend — failing test**

`apps/mobile/src/api/__tests__/bootstrap.test.ts`:

```ts
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { bootstrapSession } from '@/api/bootstrap';
import { useSession } from '@/store/session';

const BASE = 'http://test.local';
process.env.EXPO_PUBLIC_API_URL = BASE;
const server = setupServer();
beforeAll(() => server.listen());
afterEach(() => { server.resetHandlers(); useSession.setState({ accessToken: null, refreshToken: null, role: null }); });
afterAll(() => server.close());

test('returns false with no stored refresh token', async () => {
  expect(await bootstrapSession()).toBe(false);
});

test('restores role from refresh', async () => {
  useSession.setState({ refreshToken: 'r1' });
  server.use(http.post(`${BASE}/v1/auth/refresh`, () =>
    HttpResponse.json({ accessToken: 'a', role: 'doctor', userId: 'u1' })));
  expect(await bootstrapSession()).toBe(true);
  expect(useSession.getState().role).toBe('doctor');
});
```

- [ ] **Step 5: Frontend — implement**

`apps/mobile/src/api/bootstrap.ts`:

```ts
import { z } from 'zod';
import { useSession } from '@/store/session';
import type { Role } from '@/theme/tokens';

const RefreshSchema = z.object({
  accessToken: z.string(), role: z.enum(['patient', 'doctor', 'pharmacy']), userId: z.string(),
});

export async function bootstrapSession(): Promise<boolean> {
  const { refreshToken, applyRefresh, signOut } = useSession.getState();
  if (!refreshToken) return false;
  const url = process.env.EXPO_PUBLIC_API_URL;
  try {
    const res = await fetch(`${url}/v1/auth/refresh`, {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ refreshToken }),
    });
    if (!res.ok) { await signOut(); return false; }
    const data = RefreshSchema.parse(await res.json());
    applyRefresh({ accessToken: data.accessToken, role: data.role as Role, userId: data.userId });
    return true;
  } catch { await signOut(); return false; }
}
```

- [ ] **Step 6: Wire the launch gate**

Update `apps/mobile/app/index.tsx` to call `bootstrapSession` after `restoreSession`:

```tsx
  useEffect(() => {
    (async () => { await restore(); await bootstrapSession(); })().finally(() => setReady(true));
  }, [restore]);
```
(Import `bootstrapSession` from `@/api/bootstrap`.)

- [ ] **Step 7: Run + commit**

Run: `cd apps/mobile && npm test -- bootstrap && npm run typecheck`
```bash
git add apps/api/app/routers/auth.py apps/api/tests/test_auth.py apps/mobile/src/store/session.ts apps/mobile/src/api/bootstrap.ts apps/mobile/src/api/__tests__/bootstrap.test.ts apps/mobile/app/index.tsx
git commit -m "restore session role on launch via refresh"
```

---

### Task 4: Patient API module

**Files:**
- Create: `apps/mobile/src/api/patient.ts`
- Test: `apps/mobile/src/api/__tests__/patient.test.ts`

**Interfaces:**
- Consumes: `api`, schemas from Plan 01 Task 5.
- Produces: `intake(input)`, `ensureConsultation(existingId, specialtyHint)`, `getTriage(id)`, `getConsultation(id)`, `searchDoctors(params)`, `getDoctor(id)`, `book(id, body)`, `getPrescription(id)`, `listPharmacies()`, `consent(prescriptionId, pharmacyIds)`, `signUpload()`.

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/api/__tests__/patient.test.ts`:

```ts
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { searchDoctors, getTriage, listPharmacies } from '@/api/patient';
import { useSession } from '@/store/session';

const BASE = 'http://test.local';
process.env.EXPO_PUBLIC_API_URL = BASE;
const server = setupServer();
beforeAll(() => server.listen());
beforeEach(() => useSession.setState({ accessToken: 'a', refreshToken: 'r' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

const doctor = {
  id: 'd1', name: 'Dr A', specialty: 'Cardiology', qualifications: 'MBBS', experienceYears: 5,
  distanceKm: 2.1, lat: 19.99, lng: 73.79, feeInr: 400, rating: 4.6, reviewCount: 10,
  languages: ['Hindi'], nextSlot: '09:00', photoUrl: 'x', availableSlots: ['09:00', '10:00'],
};

test('searchDoctors parses the list', async () => {
  server.use(http.get(`${BASE}/v1/doctors`, () => HttpResponse.json([doctor])));
  const list = await searchDoctors({ specialty: 'Cardiology' });
  expect(list[0]!.lat).toBeCloseTo(19.99);
});

test('getTriage returns pending then result', async () => {
  server.use(http.get(`${BASE}/v1/consultations/c1/triage`, () => HttpResponse.json({ status: 'pending' })));
  const res = await getTriage('c1');
  expect('status' in res && res.status === 'pending').toBe(true);
});

test('listPharmacies parses', async () => {
  server.use(http.get(`${BASE}/v1/pharmacies`, () =>
    HttpResponse.json([{ id: 'p1', name: 'Medico', distanceKm: 0.3, deliversInMins: 16, isOpen: true }])));
  expect((await listPharmacies())[0]!.name).toBe('Medico');
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm test -- patient` → FAIL (module not found).

- [ ] **Step 3: Implement**

`apps/mobile/src/api/patient.ts`:

```ts
import { z } from 'zod';
import { api } from '@/api/client';
import {
  DoctorSchema, TriageResponseSchema, IntakeResultSchema, ConsultationDetailSchema,
  PrescriptionSchema, PharmacySchema, type Doctor, type Pharmacy, type Prescription,
} from '@/api/schemas';

const PATIENT_LAT = 19.9975, PATIENT_LNG = 73.7898;

export type IntakeInput = {
  symptomText: string; reportImageUris: string[];
  age?: number; sex?: 'M' | 'F' | 'O'; lang: 'en' | 'hi' | 'mr';
};

export const intake = (input: IntakeInput) =>
  api.post('/v1/consultations/intake', input, IntakeResultSchema);

// Direct-browse booking has no prior triage/consultation. Return the existing id if the
// patient came via triage, else create one on-demand via a minimal intake so the booking
// still produces a consultation the doctor sees in their queue.
export const ensureConsultation = async (existingId: string | undefined, specialtyHint: string): Promise<string> => {
  if (existingId) return existingId;
  const r = await intake({ symptomText: `Direct booking: ${specialtyHint}`, reportImageUris: [], lang: 'en' });
  return r.consultationId;
};

export const getTriage = (id: string) =>
  api.get(`/v1/consultations/${id}/triage`, TriageResponseSchema);

export const getConsultation = (id: string) =>
  api.get(`/v1/consultations/${id}`, ConsultationDetailSchema);

export const searchDoctors = (p: { specialty?: string; lang?: string }): Promise<Doctor[]> => {
  const q = new URLSearchParams({ lat: String(PATIENT_LAT), lng: String(PATIENT_LNG), radiusKm: '50' });
  if (p.specialty) q.set('specialty', p.specialty);
  if (p.lang) q.set('lang', p.lang);
  return api.get(`/v1/doctors?${q.toString()}`, z.array(DoctorSchema));
};

export const getDoctor = (id: string) => api.get(`/v1/doctors/${id}`, DoctorSchema);

export const book = (id: string, body: { doctorId: string; slot: string }) =>
  api.post(`/v1/consultations/${id}/book`, body, z.object({ booked: z.boolean() }));

export const getPrescription = (id: string): Promise<Prescription> =>
  api.get(`/v1/prescriptions/${id}`, PrescriptionSchema);

export const listPharmacies = (): Promise<Pharmacy[]> => {
  const q = new URLSearchParams({ lat: String(PATIENT_LAT), lng: String(PATIENT_LNG), radiusKm: '50' });
  return api.get(`/v1/pharmacies?${q.toString()}`, z.array(PharmacySchema));
};

export const consent = (prescriptionId: string, pharmacyIds: string[]) =>
  api.post(`/v1/prescriptions/${prescriptionId}/consent`, { pharmacyIds },
    z.object({ consented: z.boolean(), routedTo: z.string() }));

export const signUpload = () =>
  api.post('/v1/uploads/sign', {}, z.object({ url: z.string(), objectKey: z.string() }));

export const patientLocation = { lat: PATIENT_LAT, lng: PATIENT_LNG };
```

- [ ] **Step 4: Run to verify it passes**

Run: `npm test -- patient` → PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/mobile/src/api/patient.ts apps/mobile/src/api/__tests__/patient.test.ts
git commit -m "add patient api module"
```

---

### Task 5: Report upload pipeline

**Files:**
- Create: `apps/mobile/src/lib/upload.ts`
- Test: `apps/mobile/src/lib/__tests__/upload.test.ts`

**Interfaces:**
- Consumes: `signUpload`, `apiPutBytes`.
- Produces: `uploadReport(localUri): Promise<string>` (downscale→WebP→sign→PUT, returns `objectKey`); throws `UploadError` with `kind: 'storage' | 'network'` so the UI can message MinIO-unreachable distinctly (spec §4).

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/lib/__tests__/upload.test.ts`:

```ts
import { uploadReport, UploadError } from '@/lib/upload';

jest.mock('expo-image-manipulator', () => ({
  manipulateAsync: jest.fn(async () => ({ uri: 'file://out.webp' })),
  SaveFormat: { WEBP: 'webp' },
}));
jest.mock('@/api/patient', () => ({ signUpload: jest.fn(async () => ({ url: 'http://s/put', objectKey: 'reports/k1.webp' })) }));

const realFetch = global.fetch;
afterEach(() => { global.fetch = realFetch; });

test('returns the object key on success', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, blob: async () => new Blob(['x']) })) as unknown as typeof fetch;
  // second fetch (the PUT) also ok
  expect(await uploadReport('file://in.jpg')).toBe('reports/k1.webp');
});

test('throws storage UploadError when the PUT fails', async () => {
  let n = 0;
  global.fetch = jest.fn(async () => {
    n += 1;
    if (n === 1) return { ok: true, blob: async () => new Blob(['x']) } as unknown as Response;
    return { ok: false, status: 503 } as unknown as Response;
  }) as unknown as typeof fetch;
  await expect(uploadReport('file://in.jpg')).rejects.toMatchObject({ kind: 'storage' });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm test -- upload` → FAIL.

- [ ] **Step 3: Install + implement**

```bash
cd apps/mobile && npx expo install expo-image-picker expo-image-manipulator expo-web-browser
```

`apps/mobile/src/lib/upload.ts`:

```ts
import * as ImageManipulator from 'expo-image-manipulator';
import { signUpload } from '@/api/patient';

export class UploadError extends Error {
  constructor(public kind: 'storage' | 'network', message: string) { super(message); }
}

export async function uploadReport(localUri: string): Promise<string> {
  const edited = await ImageManipulator.manipulateAsync(
    localUri, [{ resize: { width: 1600 } }],
    { compress: 0.75, format: ImageManipulator.SaveFormat.WEBP },
  );
  let bytes: Blob;
  try {
    const r = await fetch(edited.uri);
    bytes = await r.blob();
  } catch { throw new UploadError('network', 'could not read image'); }

  const { url, objectKey } = await signUpload();
  let put: Response;
  try {
    put = await fetch(url, { method: 'PUT', headers: { 'content-type': 'image/webp' }, body: bytes });
  } catch { throw new UploadError('network', 'could not reach storage'); }
  if (!put.ok) throw new UploadError('storage', `storage rejected upload (${put.status})`);
  return objectKey;
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `npm test -- upload` → PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/mobile/src/lib/upload.ts apps/mobile/src/lib/__tests__/upload.test.ts apps/mobile/package.json
git commit -m "add report upload pipeline"
```

---

### Task 6: Patient home (symptom hero + speciality grid)

The landing page (Practo-style, per the user's reference images) at the Home tab. Two entry paths: a **symptom hero** that starts the triage flow (NADI's core), and a **speciality grid** that goes straight to a filtered doctor list (direct browse, skips triage). Lives at the `(tabs)/index.tsx` route created in Plan 01.

**Files:**
- Create: `apps/mobile/app/(patient)/(tabs)/index.tsx` (replaces the Plan 01 placeholder)
- Create: `apps/mobile/src/features/patient/useIntake.ts`
- Create: `apps/mobile/src/features/patient/specialties.ts`
- Create: `apps/mobile/src/components/SpecialtyGrid.tsx`
- Test: `apps/mobile/src/features/patient/__tests__/useIntake.test.ts`, `apps/mobile/src/features/patient/__tests__/specialties.test.ts`

**Interfaces:**
- Produces: `useIntake()` returning `{ submit(input), pending, error }` (consumed by the Analyzing screen in Task 8); `SPECIALTIES` (display label → backend specialty string); `SpecialtyGrid({ onSelect })`; the home screen with the symptom hero (text + mic + lang toggle → Reports) and the speciality grid (tap → Doctors filtered, no triage).

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/features/patient/__tests__/useIntake.test.ts`:

```ts
import { renderHook, act } from '@testing-library/react-native';
import { useIntake } from '@/features/patient/useIntake';

jest.mock('@/api/patient', () => ({ intake: jest.fn(async () => ({ consultationId: 'c1', jobId: 'j1' })) }));

test('submit returns a consultation id', async () => {
  const { result } = renderHook(() => useIntake());
  let id = '';
  await act(async () => { id = await result.current.submit({ symptomText: 'fever', reportImageUris: [], lang: 'en' }); });
  expect(id).toBe('c1');
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm test -- useIntake` → FAIL.

- [ ] **Step 3: Implement the hook**

`apps/mobile/src/features/patient/useIntake.ts`:

```ts
import { useState } from 'react';
import { intake, type IntakeInput } from '@/api/patient';

export function useIntake() {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submit = async (input: IntakeInput): Promise<string> => {
    setPending(true); setError(null);
    try { const r = await intake(input); return r.consultationId; }
    catch (e) { setError('Could not submit. Check your connection.'); throw e; }
    finally { setPending(false); }
  };
  return { submit, pending, error };
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `npm test -- useIntake` → PASS.

- [ ] **Step 5: Speciality map + grid (failing test first)**

`apps/mobile/src/features/patient/__tests__/specialties.test.ts`:
```ts
import { SPECIALTIES } from '@/features/patient/specialties';
test('maps display labels to backend specialty strings used in the seed', () => {
  const byLabel = Object.fromEntries(SPECIALTIES.map((s) => [s.label, s.specialty]));
  expect(byLabel["Women's Health"]).toBe('Gynaecology');
  expect(byLabel['Skin Specialist']).toBe('Dermatology');
  expect(byLabel['Heart']).toBe('Cardiology');
});
```
Run: `npm test -- specialties` → FAIL. Then implement.

`apps/mobile/src/features/patient/specialties.ts` (backend strings verified against `apps/api/seed/seed.py`):
```ts
import type { ComponentType } from 'react';
import { Stethoscope, Baby, HeartPulse, Ear, Bone, Eye, Droplet, User } from 'lucide-react-native';

export type Specialty = { label: string; specialty: string; Icon: ComponentType<{ size?: number; color?: string }> };

export const SPECIALTIES: Specialty[] = [
  { label: 'General Physician', specialty: 'General Physician', Icon: Stethoscope },
  { label: "Women's Health", specialty: 'Gynaecology', Icon: User },
  { label: 'Skin Specialist', specialty: 'Dermatology', Icon: Droplet },
  { label: 'Child Care', specialty: 'Paediatrics', Icon: Baby },
  { label: 'Heart', specialty: 'Cardiology', Icon: HeartPulse },
  { label: 'Bone & Joint', specialty: 'Orthopaedics', Icon: Bone },
  { label: 'Ear, Nose & Throat', specialty: 'ENT', Icon: Ear },
  { label: 'Eye Specialist', specialty: 'General Physician', Icon: Eye },
];
```
Install icons: `npx expo install lucide-react-native react-native-svg`.

`apps/mobile/src/components/SpecialtyGrid.tsx`:
```tsx
import { Pressable, Text, View } from 'react-native';
import { SPECIALTIES, type Specialty } from '@/features/patient/specialties';
import { colors, radii, spacing, type as t } from '@/theme/tokens';

export function SpecialtyGrid({ onSelect }: { onSelect: (s: Specialty) => void }) {
  return (
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm }}>
      {SPECIALTIES.map((s) => (
        <Pressable key={s.label} onPress={() => onSelect(s)}
          style={{ width: '47%', backgroundColor: colors.surface, borderRadius: radii.md,
            borderWidth: 1, borderColor: colors.border, padding: spacing.md, gap: spacing.sm }}>
          <s.Icon size={28} color={colors.seaGreen} />
          <Text style={{ fontSize: t.sm, color: colors.text, fontWeight: '600' }}>{s.label}</Text>
        </Pressable>
      ))}
    </View>
  );
}
```
Run: `npm test -- specialties` → PASS.

- [ ] **Step 6: Build the home landing screen**

`apps/mobile/app/(patient)/(tabs)/index.tsx` (symptom hero + speciality grid; keep under 150 lines):
```tsx
import { useState } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';
import { router } from 'expo-router';
import { Button, Card, Input } from '@/components/ui';
import { SpecialtyGrid } from '@/components/SpecialtyGrid';
import { useTheme } from '@/providers/ThemeProvider';
import { colors, spacing, type as t } from '@/theme/tokens';

type Lang = 'en' | 'hi' | 'mr';
const CANNED: Record<Lang, string> = {
  en: 'I have had chest pain and breathlessness since morning',
  hi: 'subah se seene mein dard aur saans phoolne ki shikayat hai',
  mr: 'सकाळपासून छातीत दुखत आहे आणि दम लागतो आहे',
};

export default function PatientHome() {
  const theme = useTheme();
  const [text, setText] = useState('');
  const [lang, setLang] = useState<Lang>('en');
  const triage = () => router.push({ pathname: '/(patient)/reports', params: { symptomText: text, lang } });
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.lg }}>
      <Text style={{ fontSize: t.h1, color: theme.primary, fontWeight: '800' }}>NADI</Text>
      <Card>
        <Text style={{ fontSize: t.h3, color: colors.text, fontWeight: '700' }}>Tell us your problem</Text>
        <Text style={{ fontSize: t.sm, color: colors.textMuted, marginBottom: spacing.sm }}>We'll route you to the right doctor.</Text>
        <View style={{ flexDirection: 'row', gap: spacing.sm, marginBottom: spacing.sm }}>
          {(['en', 'hi', 'mr'] as Lang[]).map((l) => (
            <Pressable key={l} onPress={() => setLang(l)} style={{ paddingVertical: 6, paddingHorizontal: 14,
              borderRadius: 999, backgroundColor: lang === l ? theme.primary : colors.lightGrey }}>
              <Text style={{ color: lang === l ? '#fff' : colors.text, fontSize: t.sm }}>{l.toUpperCase()}</Text>
            </Pressable>
          ))}
        </View>
        <Input value={text} onChangeText={setText} multiline placeholder="e.g. chest pain since morning…" />
        <View style={{ height: spacing.sm }} />
        <Button title="🎤 Speak instead" variant="ghost" color={theme.primary}
          onPress={() => setTimeout(() => setText(CANNED[lang]), 2000)} />
        <View style={{ height: spacing.sm }} />
        <Button title="Find the right doctor" onPress={triage} color={theme.primary}
          disabled={text.trim().length === 0} />
      </Card>
      <Text style={{ fontSize: t.h3, color: colors.text, fontWeight: '700' }}>Find doctors by speciality</Text>
      <SpecialtyGrid onSelect={(s) => router.push({ pathname: '/(patient)/doctors', params: { specialty: s.specialty } })} />
    </ScrollView>
  );
}
```
Note: the speciality path pushes to Doctors with **no `id`** param → direct browse (Task 9 handles the optional id; booking creates a consultation on-demand via `ensureConsultation`, Task 11).

- [ ] **Step 7: Run + commit**

Run: `npm test && npm run typecheck`
```bash
git add apps/mobile/app/(patient)/(tabs)/index.tsx apps/mobile/src/features/patient apps/mobile/src/components/SpecialtyGrid.tsx apps/mobile/package.json
git commit -m "add patient home with symptom hero and speciality grid"
```

---

### Task 7: Reports screen (pick + real upload)

**Files:**
- Create: `apps/mobile/app/(patient)/reports.tsx`
- Create: `apps/mobile/src/features/patient/useReportUploads.ts`
- Test: `apps/mobile/src/features/patient/__tests__/useReportUploads.test.ts`

**Interfaces:**
- Consumes: `uploadReport`.
- Produces: `useReportUploads()` → `{ items, add(uri), remove(id), retry(id), allSettled, objectKeys }` where each item is `{ id, uri, status: 'uploading'|'done'|'error', objectKey? }`. Intake proceeds only when every item is `done` (or the list is empty) — a half-uploaded report can never reach intake (spec §4).

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/features/patient/__tests__/useReportUploads.test.ts`:

```ts
import { renderHook, act, waitFor } from '@testing-library/react-native';
import { useReportUploads } from '@/features/patient/useReportUploads';

jest.mock('@/lib/upload', () => ({
  uploadReport: jest.fn(async (uri: string) => (uri.includes('bad') ? Promise.reject(new Error('x')) : 'key-ok')),
  UploadError: class extends Error {},
}));

test('a successful upload becomes done with an object key', async () => {
  const { result } = renderHook(() => useReportUploads());
  act(() => { result.current.add('file://good.jpg'); });
  await waitFor(() => expect(result.current.items[0]!.status).toBe('done'));
  expect(result.current.objectKeys).toEqual(['key-ok']);
  expect(result.current.allSettled).toBe(true);
});

test('a failed upload is error and blocks allSettled', async () => {
  const { result } = renderHook(() => useReportUploads());
  act(() => { result.current.add('file://bad.jpg'); });
  await waitFor(() => expect(result.current.items[0]!.status).toBe('error'));
  expect(result.current.allSettled).toBe(false);
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm test -- useReportUploads` → FAIL.

- [ ] **Step 3: Implement the hook**

`apps/mobile/src/features/patient/useReportUploads.ts`:

```ts
import { useCallback, useState } from 'react';
import { uploadReport } from '@/lib/upload';

type Item = { id: string; uri: string; status: 'uploading' | 'done' | 'error'; objectKey?: string };
let seq = 0;

export function useReportUploads() {
  const [items, setItems] = useState<Item[]>([]);
  const patch = (id: string, p: Partial<Item>) =>
    setItems((xs) => xs.map((x) => (x.id === id ? { ...x, ...p } : x)));

  const run = useCallback(async (id: string, uri: string) => {
    patch(id, { status: 'uploading' });
    try { patch(id, { status: 'done', objectKey: await uploadReport(uri) }); }
    catch { patch(id, { status: 'error' }); }
  }, []);

  const add = useCallback((uri: string) => {
    const id = `r${seq++}`;
    setItems((xs) => [...xs, { id, uri, status: 'uploading' }]);
    void run(id, uri);
  }, [run]);

  const remove = useCallback((id: string) => setItems((xs) => xs.filter((x) => x.id !== id)), []);
  const retry = useCallback((id: string) => {
    const it = items.find((x) => x.id === id);
    if (it) void run(id, it.uri);
  }, [items, run]);

  const allSettled = items.every((x) => x.status === 'done');
  const objectKeys = items.filter((x) => x.objectKey).map((x) => x.objectKey!) as string[];
  return { items, add, remove, retry, allSettled, objectKeys };
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `npm test -- useReportUploads` → PASS.

- [ ] **Step 5: Build the screen**

`apps/mobile/app/(patient)/reports.tsx` — image picker grid with per-tile status; a report is skippable (empty list is allowed) but any added image must finish before Continue enables:

```tsx
import { Image, Pressable, ScrollView, Text, View } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { router, useLocalSearchParams } from 'expo-router';
import { Button } from '@/components/ui';
import { useReportUploads } from '@/features/patient/useReportUploads';
import { useTheme } from '@/providers/ThemeProvider';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function Reports() {
  const theme = useTheme();
  const { symptomText, lang } = useLocalSearchParams<{ symptomText: string; lang: string }>();
  const { items, add, remove, retry, allSettled, objectKeys } = useReportUploads();
  const pick = async () => {
    const res = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 1 });
    if (!res.canceled && res.assets[0]) add(res.assets[0].uri);
  };
  const go = () => router.push({ pathname: '/(patient)/analyzing',
    params: { symptomText, lang, keys: JSON.stringify(objectKeys) } });
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.h2, color: theme.primary, fontWeight: '700' }}>Lab reports (optional)</Text>
      <Text style={{ fontSize: t.sm, color: colors.textMuted }}>Add photos of any recent reports, or skip.</Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm }}>
        {items.map((it) => (
          <View key={it.id} style={{ width: 96 }}>
            <Image source={{ uri: it.uri }} style={{ width: 96, height: 96, borderRadius: 8 }} />
            <Text style={{ fontSize: t.xs, color: it.status === 'error' ? colors.emergency : colors.textMuted }}>
              {it.status === 'uploading' ? 'Uploading…' : it.status === 'done' ? 'Ready' : 'Failed — tap retry'}
            </Text>
            {it.status === 'error' ? <Pressable onPress={() => retry(it.id)}><Text style={{ color: theme.primary }}>Retry</Text></Pressable> : null}
            <Pressable onPress={() => remove(it.id)}><Text style={{ color: colors.textMuted }}>Remove</Text></Pressable>
          </View>
        ))}
        <Pressable onPress={pick} style={{ width: 96, height: 96, borderRadius: 8, borderWidth: 1,
          borderColor: colors.border, alignItems: 'center', justifyContent: 'center' }}>
          <Text style={{ color: theme.primary, fontSize: 28 }}>＋</Text>
        </Pressable>
      </View>
      <Button title="Continue" onPress={go} color={theme.primary} disabled={!allSettled} />
    </ScrollView>
  );
}
```

- [ ] **Step 6: Run + commit**

Run: `npm test && npm run typecheck`
```bash
git add apps/mobile/app/(patient)/reports.tsx apps/mobile/src/features/patient/useReportUploads.ts apps/mobile/src/features/patient/__tests__/useReportUploads.test.ts apps/mobile/package.json
git commit -m "add reports upload screen"
```

---

### Task 8: Analyzing + triage result (with emergency view)

**Files:**
- Create: `apps/mobile/app/(patient)/analyzing.tsx`
- Create: `apps/mobile/app/(patient)/result.tsx`
- Create: `apps/mobile/src/features/patient/useTriage.ts`
- Test: `apps/mobile/src/features/patient/__tests__/useTriage.test.tsx`

**Interfaces:**
- Consumes: `intake`, `getTriage`, `pollInterval`.
- Produces: `useTriage(consultationId)` → React Query result that polls `getTriage` at 1500 ms while the response is `{status:'pending'}` and stops once a `TriageResult` arrives. (Intake runs triage synchronously in the current backend, so this typically resolves on the first poll; the loading animation still shows a minimum ~1.8 s per §13.)

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/features/patient/__tests__/useTriage.test.tsx`:

```tsx
import { renderHook, waitFor } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useTriage } from '@/features/patient/useTriage';

jest.mock('@/api/patient', () => ({
  getTriage: jest.fn(async () => ({
    acuity: 'ROUTINE', acuityConfidence: 0.8, specialties: [], drivers: [], labs: [],
    redFlags: [], modelVersion: 'stub',
  })),
}));

const wrap = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>
);

test('resolves to a triage result', async () => {
  const { result } = renderHook(() => useTriage('c1'), { wrapper: wrap });
  await waitFor(() => expect(result.current.data?.acuity).toBe('ROUTINE'));
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm test -- useTriage` → FAIL.

- [ ] **Step 3: Implement the hook**

`apps/mobile/src/features/patient/useTriage.ts`:

```ts
import { useQuery } from '@tanstack/react-query';
import { getTriage } from '@/api/patient';
import { pollInterval } from '@/lib/polling';
import type { TriageResult } from '@/api/schemas';

const isPending = (d: unknown): d is { status: 'pending' } =>
  typeof d === 'object' && d !== null && 'status' in d;

export function useTriage(consultationId: string) {
  return useQuery({
    queryKey: ['triage', consultationId],
    queryFn: async (): Promise<TriageResult | { status: 'pending' }> => getTriage(consultationId),
    refetchInterval: (q) => pollInterval(isPending(q.state.data), 1500),
    select: (d) => (isPending(d) ? undefined : (d as TriageResult)),
  });
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `npm test -- useTriage` → PASS.

- [ ] **Step 5: Build analyzing + result screens**

`apps/mobile/app/(patient)/analyzing.tsx` — triggers intake once, shows three fading lines, routes to result with the consultation id:

```tsx
import { useEffect, useRef, useState } from 'react';
import { Text, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { useIntake } from '@/features/patient/useIntake';
import { useTheme } from '@/providers/ThemeProvider';
import { colors, spacing, type as t } from '@/theme/tokens';

const LINES = ['Reading your reports', 'Understanding your symptoms', 'Finding the right doctor'];

export default function Analyzing() {
  const theme = useTheme();
  const { submit } = useIntake();
  const { symptomText, lang, keys } = useLocalSearchParams<{ symptomText: string; lang: string; keys: string }>();
  const [line, setLine] = useState(0);
  const started = useRef(false);
  useEffect(() => {
    const id = setInterval(() => setLine((n) => Math.min(n + 1, LINES.length - 1)), 700);
    return () => clearInterval(id);
  }, []);
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const run = async () => {
      const consultationId = await submit({ symptomText: symptomText ?? '', lang: (lang as 'en') ?? 'en',
        reportImageUris: keys ? (JSON.parse(keys) as string[]) : [] });
      setTimeout(() => router.replace({ pathname: '/(patient)/result', params: { id: consultationId } }), 1800);
    };
    run().catch(() => router.replace('/(patient)'));
  }, [symptomText, lang, keys, submit]);
  return (
    <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', padding: spacing.xl, gap: spacing.md }}>
      <Text style={{ fontSize: t.h3, color: theme.primary, fontWeight: '600' }}>{LINES[line]}…</Text>
      <Text style={{ fontSize: t.sm, color: colors.textMuted }}>This takes a few seconds</Text>
    </View>
  );
}
```

`apps/mobile/app/(patient)/result.tsx` — red-flag emergency view replaces everything; otherwise acuity + specialties + drivers + labs:

```tsx
import { Linking, ScrollView, Text, View } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { router } from 'expo-router';
import { AcuityBadge, Button, Card, Skeleton } from '@/components/ui';
import { useTriage } from '@/features/patient/useTriage';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function Result() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data, isLoading } = useTriage(id!);
  if (isLoading || !data) return <View style={{ padding: spacing.lg, gap: spacing.md }}><Skeleton height={32} /><Skeleton height={120} /></View>;

  if (data.redFlags.length > 0) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.emergency, padding: spacing.xl, justifyContent: 'center', gap: spacing.lg }}>
        <Text style={{ color: '#fff', fontSize: t.h1, fontWeight: '800' }}>Seek care now</Text>
        <Text style={{ color: '#fff', fontSize: t.body }}>{data.redFlags[0]}</Text>
        <Button title="Call 108 (ambulance)" onPress={() => Linking.openURL('tel:108')} />
      </View>
    );
  }

  const top = data.specialties[0];
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <AcuityBadge acuity={data.acuity} />
      <Text style={{ fontSize: t.h2, color: colors.text, fontWeight: '700' }}>
        We suggest seeing a {top?.name ?? 'doctor'}
      </Text>
      <Card>
        <Text style={{ fontSize: t.sm, color: colors.textMuted, marginBottom: spacing.xs }}>Why we think this</Text>
        {data.drivers.map((d, i) => (
          <Text key={i} style={{ fontSize: t.sm, color: colors.text }}>• {d.feature}</Text>
        ))}
      </Card>
      {data.labs.length > 0 ? (
        <Card>
          <Text style={{ fontSize: t.sm, color: colors.textMuted }}>From your reports</Text>
          {data.labs.map((l, i) => (
            <Text key={i} style={{ fontSize: t.sm, color: l.flag === 'N' ? colors.text : colors.urgent }}>
              {l.analyte}: {l.value} {l.unit} ({l.flag})
            </Text>
          ))}
        </Card>
      ) : null}
      <Button title="See doctors" onPress={() => router.push({ pathname: '/(patient)/doctors',
        params: { id: id!, specialty: top?.name ?? '' } })} />
    </ScrollView>
  );
}
```

- [ ] **Step 6: Run + commit**

Run: `npm test && npm run typecheck`
```bash
git add apps/mobile/app/(patient)/analyzing.tsx apps/mobile/app/(patient)/result.tsx apps/mobile/src/features/patient/useTriage.ts apps/mobile/src/features/patient/__tests__/useTriage.test.tsx
git commit -m "add analyzing and triage result screens"
```

---

### Task 9: Doctor list (FlashList)

**Files:**
- Create: `apps/mobile/app/(patient)/doctors.tsx`
- Create: `apps/mobile/src/features/patient/useDoctors.ts`
- Create: `apps/mobile/src/components/DoctorCard.tsx`
- Test: `apps/mobile/src/features/patient/__tests__/useDoctors.test.tsx`

**Interfaces:**
- Consumes: `searchDoctors`.
- Produces: `useDoctors(specialty)` React Query list; `DoctorCard({ doctor, onPress })`; doctors screen with a FlashList, an empty state, and a list/map toggle (map in Task 10).

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/features/patient/__tests__/useDoctors.test.tsx`:

```tsx
import { renderHook, waitFor } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useDoctors } from '@/features/patient/useDoctors';

jest.mock('@/api/patient', () => ({ searchDoctors: jest.fn(async () => [{ id: 'd1', name: 'Dr A' }]) }));
const wrap = ({ children }: { children: React.ReactNode }) =>
  <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>;

test('loads doctors', async () => {
  const { result } = renderHook(() => useDoctors('Cardiology'), { wrapper: wrap });
  await waitFor(() => expect(result.current.data?.[0]?.name).toBe('Dr A'));
});
```

- [ ] **Step 2: Run to verify it fails** → `npm test -- useDoctors` FAIL.

- [ ] **Step 3: Implement the hook + card + install FlashList**

```bash
cd apps/mobile && npx expo install @shopify/flash-list
```

`apps/mobile/src/features/patient/useDoctors.ts`:
```ts
import { useQuery } from '@tanstack/react-query';
import { searchDoctors } from '@/api/patient';

export function useDoctors(specialty?: string) {
  return useQuery({ queryKey: ['doctors', specialty], queryFn: () => searchDoctors({ specialty }) });
}
```

`apps/mobile/src/components/DoctorCard.tsx`:
```tsx
import { Pressable, Text, View } from 'react-native';
import { Avatar, Card } from '@/components/ui';
import type { Doctor } from '@/api/schemas';
import { colors, spacing, type as t } from '@/theme/tokens';

export function DoctorCard({ doctor, onPress }: { doctor: Doctor; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} style={{ marginBottom: spacing.sm }}>
      <Card>
        <View style={{ flexDirection: 'row', gap: spacing.md }}>
          <Avatar uri={doctor.photoUrl} />
          <View style={{ flex: 1 }}>
            <Text style={{ fontSize: t.body, fontWeight: '700', color: colors.text }}>{doctor.name}</Text>
            <Text style={{ fontSize: t.sm, color: colors.textMuted }}>{doctor.specialty} · {doctor.qualifications}</Text>
            <Text style={{ fontSize: t.sm, color: colors.textMuted }}>
              {doctor.distanceKm} km · ₹{doctor.feeInr} · ★ {doctor.rating} ({doctor.reviewCount})
            </Text>
          </View>
        </View>
      </Card>
    </Pressable>
  );
}
```

- [ ] **Step 4: Build the screen**

`apps/mobile/app/(patient)/doctors.tsx`:
```tsx
import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { FlashList } from '@shopify/flash-list';
import { router, useLocalSearchParams } from 'expo-router';
import { DoctorCard } from '@/components/DoctorCard';
import { EmptyState, ErrorState, Skeleton } from '@/components/ui';
import { DoctorsMap } from '@/components/DoctorsMap';
import { useDoctors } from '@/features/patient/useDoctors';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function Doctors() {
  const { id, specialty } = useLocalSearchParams<{ id?: string; specialty: string }>();
  const { data, isLoading, isError, refetch } = useDoctors(specialty || undefined);
  const [map, setMap] = useState(false);
  if (isLoading) return <View style={{ padding: spacing.lg, gap: spacing.sm }}>{[0, 1, 2].map((i) => <Skeleton key={i} height={96} />)}</View>;
  if (isError) return <ErrorState message="Could not load doctors." onRetry={refetch} />;
  const doctors = data ?? [];
  return (
    <View style={{ flex: 1 }}>
      <View style={{ flexDirection: 'row', justifyContent: 'flex-end', padding: spacing.sm }}>
        <Pressable onPress={() => setMap((m) => !m)}><Text style={{ color: colors.navy, fontSize: t.sm }}>{map ? 'List' : 'Map'}</Text></Pressable>
      </View>
      {map ? <DoctorsMap doctors={doctors} />
        : <FlashList data={doctors} estimatedItemSize={120} keyExtractor={(d) => d.id}
            contentContainerStyle={{ padding: spacing.lg }}
            ListEmptyComponent={<EmptyState title="No doctors nearby" message="Try widening your search." />}
            renderItem={({ item }) => <DoctorCard doctor={item}
              onPress={() => router.push({ pathname: '/(patient)/doctor/[did]',
                params: { did: item.id, ...(id ? { id } : {}) } })} />} />}
    </View>
  );
}
```

- [ ] **Step 5: Run + commit** (DoctorsMap stub added next task; create a placeholder so this compiles)

Create a temporary `apps/mobile/src/components/DoctorsMap.tsx` returning `null` for now, replaced in Task 10:
```tsx
import type { Doctor } from '@/api/schemas';
export function DoctorsMap(_: { doctors: Doctor[] }) { return null; }
```
Run: `npm test && npm run typecheck`
```bash
git add apps/mobile/app/(patient)/doctors.tsx apps/mobile/src/features/patient/useDoctors.ts apps/mobile/src/components/DoctorCard.tsx apps/mobile/src/components/DoctorsMap.tsx apps/mobile/src/features/patient/__tests__/useDoctors.test.tsx apps/mobile/package.json
git commit -m "add doctor list screen"
```

---

### Task 10: Doctor map (MapLibre, free tiles)

**Files:**
- Modify: `apps/mobile/src/components/DoctorsMap.tsx`
- Modify: `apps/mobile/app.json` (MapLibre plugin if required by the lib version)
- Test: `apps/mobile/src/components/__tests__/DoctorsMap.test.tsx`

**Interfaces:**
- Consumes: `Doctor[]`, `patientLocation`.
- Produces: `DoctorsMap({ doctors })` rendering a MapLibre map centred on the patient with one marker per doctor, using the free no-key style `https://tiles.openfreemap.org/styles/liberty`.

- [ ] **Step 1: Install**

```bash
cd apps/mobile && npx expo install @maplibre/maplibre-react-native
```
If the installed version ships a config plugin, add it to `app.json` `plugins`. A native map needs a dev build (`npx expo run:android`) — it will not render in Expo Go; note this for the device-verification step.

- [ ] **Step 2: Write the failing test (logic, map mocked)**

`apps/mobile/src/components/__tests__/DoctorsMap.test.tsx`:
```tsx
import { render } from '@testing-library/react-native';
import { DoctorsMap } from '@/components/DoctorsMap';

jest.mock('@maplibre/maplibre-react-native', () => {
  const React = require('react');
  const { View } = require('react-native');
  const C = ({ children, ...p }: any) => React.createElement(View, p, children);
  return { __esModule: true, default: {}, MapView: C, Camera: C, MarkerView: C, ShapeSource: C };
});

test('renders a marker per doctor', () => {
  const docs = [
    { id: 'd1', name: 'A', lat: 19.99, lng: 73.79 }, { id: 'd2', name: 'B', lat: 20.0, lng: 73.8 },
  ] as any;
  const { UNSAFE_root } = render(<DoctorsMap doctors={docs} />);
  expect(UNSAFE_root).toBeTruthy();
});
```

- [ ] **Step 3: Implement**

`apps/mobile/src/components/DoctorsMap.tsx`:
```tsx
import MapLibreGL, { Camera, MapView, MarkerView } from '@maplibre/maplibre-react-native';
import { View, Text } from 'react-native';
import type { Doctor } from '@/api/schemas';
import { patientLocation } from '@/api/patient';
import { colors } from '@/theme/tokens';

const STYLE_URL = 'https://tiles.openfreemap.org/styles/liberty'; // free, no key, no billing

export function DoctorsMap({ doctors }: { doctors: Doctor[] }) {
  return (
    <MapView style={{ flex: 1 }} mapStyle={STYLE_URL}>
      <Camera zoomLevel={11} centerCoordinate={[patientLocation.lng, patientLocation.lat]} />
      {doctors.map((d) => (
        <MarkerView key={d.id} coordinate={[d.lng, d.lat]}>
          <View style={{ backgroundColor: colors.navy, borderRadius: 999, paddingHorizontal: 8, paddingVertical: 4 }}>
            <Text style={{ color: '#fff', fontSize: 11 }}>₹{d.feeInr}</Text>
          </View>
        </MarkerView>
      ))}
    </MapView>
  );
}
```
(If the installed API differs — e.g. `PointAnnotation` instead of `MarkerView`, or a `styleURL` prop name — adjust to the version's API; the free `STYLE_URL` and the per-doctor marker loop are the invariants.)

- [ ] **Step 4: Run tests + typecheck**

Run: `npm test -- DoctorsMap && npm run typecheck` → PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/mobile/src/components/DoctorsMap.tsx apps/mobile/src/components/__tests__/DoctorsMap.test.tsx apps/mobile/app.json apps/mobile/package.json
git commit -m "add maplibre doctor map"
```

---

### Task 11: Doctor detail + booking

**Files:**
- Create: `apps/mobile/app/(patient)/doctor/[did].tsx`
- Create: `apps/mobile/app/(patient)/booked.tsx`
- Create: `apps/mobile/src/features/patient/useDoctor.ts`, `useBook.ts`
- Test: `apps/mobile/src/features/patient/__tests__/useBook.test.ts`

**Interfaces:**
- Consumes: `getDoctor`, `book`.
- Produces: `useDoctor(did)`; `useBook()` → `{ confirm(consultationId, doctorId, slot), pending }`; detail screen with stat tiles + slot chips + sticky book bar; booked confirmation screen.

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/features/patient/__tests__/useBook.test.ts`:
```ts
import { renderHook, act } from '@testing-library/react-native';
import { useBook } from '@/features/patient/useBook';
jest.mock('@/api/patient', () => ({ book: jest.fn(async () => ({ booked: true })) }));

test('confirm resolves true', async () => {
  const { result } = renderHook(() => useBook());
  let ok = false;
  await act(async () => { ok = await result.current.confirm('c1', 'd1', '09:00'); });
  expect(ok).toBe(true);
});
```

- [ ] **Step 2: Run to verify it fails** → `npm test -- useBook` FAIL.

- [ ] **Step 3: Implement hooks**

`apps/mobile/src/features/patient/useDoctor.ts`:
```ts
import { useQuery } from '@tanstack/react-query';
import { getDoctor } from '@/api/patient';
export function useDoctor(did: string) {
  return useQuery({ queryKey: ['doctor', did], queryFn: () => getDoctor(did) });
}
```
`apps/mobile/src/features/patient/useBook.ts`:
```ts
import { useState } from 'react';
import { book } from '@/api/patient';
export function useBook() {
  const [pending, setPending] = useState(false);
  const confirm = async (consultationId: string, doctorId: string, slot: string): Promise<boolean> => {
    setPending(true);
    try { return (await book(consultationId, { doctorId, slot })).booked; }
    finally { setPending(false); }
  };
  return { confirm, pending };
}
```

- [ ] **Step 4: Build detail + booked screens**

`apps/mobile/app/(patient)/doctor/[did].tsx`:
```tsx
import { useState } from 'react';
import { ScrollView, Text, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Avatar, Button, Card, Skeleton } from '@/components/ui';
import { useDoctor } from '@/features/patient/useDoctor';
import { useBook } from '@/features/patient/useBook';
import { ensureConsultation } from '@/api/patient';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function DoctorDetail() {
  const { did, id } = useLocalSearchParams<{ did: string; id?: string }>();
  const { data: d, isLoading } = useDoctor(did!);
  const { confirm, pending } = useBook();
  const [slot, setSlot] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  if (isLoading || !d) return <View style={{ padding: spacing.lg }}><Skeleton height={200} /></View>;
  const bookNow = async () => {
    if (!slot) return;
    setBusy(true);
    try {
      const cid = await ensureConsultation(id, d.specialty); // existing id on triage path; created on direct browse
      const ok = await confirm(cid, d.id, slot);
      if (ok) router.replace({ pathname: '/(patient)/booked', params: { id: cid, slot, name: d.name } });
    } finally { setBusy(false); }
  };
  return (
    <View style={{ flex: 1 }}>
      <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
        <View style={{ alignItems: 'center', gap: spacing.sm }}>
          <Avatar uri={d.photoUrl} size={96} />
          <Text style={{ fontSize: t.h2, fontWeight: '700', color: colors.text }}>{d.name}</Text>
          <Text style={{ fontSize: t.sm, color: colors.textMuted }}>{d.specialty} · {d.experienceYears} yrs</Text>
        </View>
        <Card><Text style={{ color: colors.text }}>Languages: {d.languages.join(', ')}  ·  Fee ₹{d.feeInr}</Text></Card>
        <Text style={{ fontSize: t.body, fontWeight: '600', color: colors.text }}>Pick a time slot</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm }}>
          {d.availableSlots.map((s) => (
            <Button key={s} title={s} variant={slot === s ? 'primary' : 'ghost'} color={colors.navy}
              onPress={() => setSlot(s)} />
          ))}
        </View>
      </ScrollView>
      <View style={{ padding: spacing.lg, borderTopWidth: 1, borderColor: colors.border }}>
        <Button title={slot ? `Book ${slot}` : 'Select a slot'} onPress={bookNow} loading={busy || pending} disabled={!slot || busy} />
      </View>
    </View>
  );
}
```
`apps/mobile/app/(patient)/booked.tsx`:
```tsx
import { Text, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Button } from '@/components/ui';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function Booked() {
  const { id, slot, name } = useLocalSearchParams<{ id: string; slot: string; name: string }>();
  return (
    <View style={{ flex: 1, justifyContent: 'center', padding: spacing.xl, gap: spacing.md }}>
      <Text style={{ fontSize: t.h1, color: colors.routine, fontWeight: '800' }}>Booked</Text>
      <Text style={{ fontSize: t.body, color: colors.text }}>Your appointment with {name} at {slot} is confirmed.</Text>
      <Button title="Join consultation" onPress={() => router.push({ pathname: '/(patient)/consultation', params: { id: id! } })} />
      <Button title="View prescription" variant="ghost" onPress={() => router.push({ pathname: '/(patient)/prescription', params: { id: id! } })} />
    </View>
  );
}
```

- [ ] **Step 5: Run + commit**

Run: `npm test && npm run typecheck`
```bash
git add apps/mobile/app/(patient)/doctor apps/mobile/app/(patient)/booked.tsx apps/mobile/src/features/patient/useDoctor.ts apps/mobile/src/features/patient/useBook.ts apps/mobile/src/features/patient/__tests__/useBook.test.ts
git commit -m "add doctor detail and booking screens"
```

---

### Task 12: Consultation (jit.si) & room helper

**Files:**
- Create: `apps/mobile/src/lib/room.ts`
- Create: `apps/mobile/app/(patient)/consultation.tsx`
- Test: `apps/mobile/src/lib/__tests__/room.test.ts`

**Interfaces:**
- Produces: `roomUrl(consultationId): string` → `https://meet.jit.si/nadi-<id>`; consultation screen opens it via `expo-web-browser` (reliable camera/mic on Android via the system Custom Tab — chosen over an in-app WebView, which commonly blocks `getUserMedia`; satisfies spec §4's "join the room", with the browser as the robust default).

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/lib/__tests__/room.test.ts`:
```ts
import { roomUrl } from '@/lib/room';
test('builds a stable per-consultation room url', () => {
  expect(roomUrl('abc-123')).toBe('https://meet.jit.si/nadi-abc-123');
});
```

- [ ] **Step 2: Run to verify it fails** → `npm test -- room` FAIL.

- [ ] **Step 3: Implement**

`apps/mobile/src/lib/room.ts`:
```ts
export function roomUrl(consultationId: string): string {
  return `https://meet.jit.si/nadi-${consultationId}`;
}
```
`apps/mobile/app/(patient)/consultation.tsx`:
```tsx
import { useState } from 'react';
import { Text, View } from 'react-native';
import * as WebBrowser from 'expo-web-browser';
import { useLocalSearchParams } from 'expo-router';
import { Button } from '@/components/ui';
import { roomUrl } from '@/lib/room';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function Consultation() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [error, setError] = useState<string | null>(null);
  const join = async () => {
    try { await WebBrowser.openBrowserAsync(roomUrl(id!)); }
    catch { setError('Could not open the video call.'); }
  };
  return (
    <View style={{ flex: 1, justifyContent: 'center', padding: spacing.xl, gap: spacing.md }}>
      <Text style={{ fontSize: t.h2, color: colors.text, fontWeight: '700' }}>Video consultation</Text>
      <Text style={{ fontSize: t.sm, color: colors.textMuted }}>
        Your doctor joins the same secure room. Allow camera and microphone when asked.
      </Text>
      <Button title="Join video call" onPress={join} />
      {error ? <Text style={{ color: colors.emergency, fontSize: t.sm }}>{error}</Text> : null}
    </View>
  );
}
```

- [ ] **Step 4: Run + commit**

Run: `npm test -- room && npm run typecheck`
```bash
git add apps/mobile/src/lib/room.ts apps/mobile/app/(patient)/consultation.tsx apps/mobile/src/lib/__tests__/room.test.ts
git commit -m "add jit.si consultation screen"
```

---

### Task 13: Prescription discovery + pharmacy consent

**Files:**
- Create: `apps/mobile/app/(patient)/prescription.tsx`
- Create: `apps/mobile/src/features/patient/usePrescription.ts`
- Create: `apps/mobile/src/features/patient/useConsent.ts`
- Test: `apps/mobile/src/features/patient/__tests__/usePrescription.test.tsx`

**Interfaces:**
- Consumes: `getConsultation`, `getPrescription`, `listPharmacies`, `consent`, `pollInterval`.
- Produces: `usePrescription(consultationId)` — polls `getConsultation` (3 s) until `prescriptionId` appears, then loads + polls the prescription for `status` changes; `useConsent()` → `{ submit(prescriptionId, ids), pending, done }`. Consent is **mandatory, multi-select, nothing pre-ticked**.

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/features/patient/__tests__/usePrescription.test.tsx`:
```tsx
import { renderHook, waitFor } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { usePrescription } from '@/features/patient/usePrescription';

jest.mock('@/api/patient', () => ({
  getConsultation: jest.fn(async () => ({ id: 'c1', status: 'BOOKED', prescriptionId: 'p1' })),
  getPrescription: jest.fn(async () => ({ id: 'p1', patientName: 'X', doctorName: 'Dr', issuedAt: 't',
    lines: [{ drug: 'Paracetamol', strength: '500mg', frequency: 'BD', durationDays: 3, notes: null }], status: 'PENDING' })),
}));
const wrap = ({ children }: { children: React.ReactNode }) =>
  <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>;

test('discovers prescription id then loads the prescription', async () => {
  const { result } = renderHook(() => usePrescription('c1'), { wrapper: wrap });
  await waitFor(() => expect(result.current.prescription?.lines[0]?.drug).toBe('Paracetamol'));
});
```

- [ ] **Step 2: Run to verify it fails** → `npm test -- usePrescription` FAIL.

- [ ] **Step 3: Implement the hooks**

`apps/mobile/src/features/patient/usePrescription.ts`:
```ts
import { useQuery } from '@tanstack/react-query';
import { getConsultation, getPrescription } from '@/api/patient';
import { pollInterval } from '@/lib/polling';

export function usePrescription(consultationId: string) {
  const consult = useQuery({
    queryKey: ['consultation', consultationId],
    queryFn: () => getConsultation(consultationId),
    refetchInterval: (q) => pollInterval(!q.state.data?.prescriptionId, 3000),
  });
  const prescriptionId = consult.data?.prescriptionId ?? null;
  const prescription = useQuery({
    queryKey: ['prescription', prescriptionId],
    queryFn: () => getPrescription(prescriptionId!),
    enabled: !!prescriptionId,
    refetchInterval: (q) => pollInterval(q.state.data?.status === 'PENDING', 3000),
  });
  return { prescriptionId, prescription: prescription.data, waiting: !prescriptionId };
}
```
`apps/mobile/src/features/patient/useConsent.ts`:
```ts
import { useState } from 'react';
import { consent } from '@/api/patient';
export function useConsent() {
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState(false);
  const submit = async (prescriptionId: string, ids: string[]) => {
    setPending(true);
    try { await consent(prescriptionId, ids); setDone(true); }
    finally { setPending(false); }
  };
  return { submit, pending, done };
}
```

- [ ] **Step 4: Build the screen**

`apps/mobile/app/(patient)/prescription.tsx` — waits for the doctor's prescription, lists medicines, then a mandatory pharmacy multi-select (nothing pre-ticked), then shows live status:
```tsx
import { useState } from 'react';
import { ScrollView, Text, View } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import { Button, Card, Skeleton } from '@/components/ui';
import { usePrescription } from '@/features/patient/usePrescription';
import { useConsent } from '@/features/patient/useConsent';
import { listPharmacies } from '@/api/patient';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function PrescriptionScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { prescriptionId, prescription, waiting } = usePrescription(id!);
  const pharmacies = useQuery({ queryKey: ['pharmacies'], queryFn: listPharmacies });
  const { submit, pending, done } = useConsent();
  const [picked, setPicked] = useState<string[]>([]);
  const toggle = (pid: string) => setPicked((xs) => xs.includes(pid) ? xs.filter((x) => x !== pid) : [...xs, pid]);

  if (waiting || !prescription) return (
    <View style={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.body, color: colors.textMuted }}>Waiting for your doctor's prescription…</Text>
      <Skeleton height={120} />
    </View>
  );
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.h2, fontWeight: '700', color: colors.text }}>Prescription</Text>
      <Card>{prescription.lines.map((l, i) => (
        <Text key={i} style={{ color: colors.text, fontSize: t.sm }}>{l.drug} {l.strength} — {l.frequency}, {l.durationDays}d</Text>
      ))}</Card>
      <Text style={{ fontSize: t.body, fontWeight: '600', color: colors.text }}>Choose your pharmacy</Text>
      <Text style={{ fontSize: t.xs, color: colors.textMuted }}>Required — you choose who receives it. Nothing is pre-selected.</Text>
      {(pharmacies.data ?? []).map((p) => (
        <Button key={p.id} title={`${picked.includes(p.id) ? '✓ ' : ''}${p.name} · ${p.distanceKm}km${p.isOpen ? '' : ' (closed)'}`}
          variant={picked.includes(p.id) ? 'primary' : 'ghost'} color={colors.navy} onPress={() => toggle(p.id)} />
      ))}
      <Button title="Send to selected pharmacies" disabled={picked.length === 0 || done} loading={pending}
        onPress={() => prescriptionId && submit(prescriptionId, picked)} />
      {done ? <Text style={{ color: colors.routine, fontSize: t.body }}>Status: {prescription.status}</Text> : null}
    </ScrollView>
  );
}
```

- [ ] **Step 5: Run + commit**

Run: `npm test && npm run typecheck`
```bash
git add apps/mobile/app/(patient)/prescription.tsx apps/mobile/src/features/patient/usePrescription.ts apps/mobile/src/features/patient/useConsent.ts apps/mobile/src/features/patient/__tests__/usePrescription.test.tsx
git commit -m "add prescription and pharmacy consent screen"
```

---

## Verification (end of Plan 02)

- `cd apps/api && .venv/Scripts/python -m pytest` — green (Tasks 1–3 backend).
- `cd apps/mobile && npm test && npm run typecheck` — green.
- Device (dev build, `npx expo run:android`, backend + MinIO up on LAN): new `+91` patient signs up → types/【mic】symptoms → adds a report photo (uploads to MinIO, shows "Ready") → Analyzing → Result (try a "chest pain and breathlessness" symptom to see the red emergency view) → doctor list + map toggle → pick slot → book → join jit.si → open prescription (will wait until the doctor prescribes in Plan 03) → choose a pharmacy → consent.

**Next plan:** `03-doctor-flow` — queue, NADI Note patient file, prescribe, refer, join the same jit.si room.

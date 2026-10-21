# NADI Frontend — Plan 05: Doctor Portal (v2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Depends on Plans 01–03.**

**Goal:** Build out the full "Nadi Pariksha" doctor portal on top of the minimal Plan 03 doctor flow — a dashboard with real stats, a dated appointments board, a patient medical-history file, prescriptions and lab-report lists, an availability editor, and a profile screen — all driven by the merged v2 backend endpoints (`/v1/doctor/*`, `/v1/medicines`, consultation notes). Medicine search is added to the prescription form.

**Architecture:** The doctor portal stays a single themed Stack (navy, no tabs — a focused professional tool per spec §1). This plan **repurposes `(doctor)/index.tsx` as the dashboard** (Plan 03 made it the queue) and **relocates the queue to `(doctor)/queue.tsx`** — same component, new route. Every other v2 screen is a stack-pushed route reachable from the dashboard. All network lives in a new `src/api/doctorPortal.ts` beside the existing `src/api/doctor.ts`; every response is zod-parsed at the boundary. Reads that must stay live (appointments, lab reports) use React Query; static-per-session reads (profile, availability) load once.

**Tech Stack:** Plan 01–03 stack — expo-router, React Query, zod, NativeWind, Reanimated, `@shopify/flash-list`, `expo-image`, `lucide-react-native`. No new runtime dependencies.

## Global Constraints

(Same as Plans 01–03 — repeated for self-containment.)

- TS strict; no `any`, no `@ts-ignore`; functional components **<150 lines**; no business logic in route files; **tokens only, no inline hex**.
- Baseline 360×640; tap targets ≥48dp; primary buttons 56dp; body ≥15; type scale 30/24/20/17/15/13.
- Acuity always a coloured **badge + text label**, never colour alone (colour-blind-safe).
- No AI/tool attribution anywhere; commit messages short, imperative, lowercase.
- **The system routes, it does not diagnose** — the NADI Note and patient file present routing + history, never a diagnosis.
- **A doctor sees only their own patients/appointments** — enforced server-side (`require_role("doctor")` + `owned_by_doctor`); the UI never implies broader access (ProjectPlan §11).
- Strictly $0; access token memory / refresh in SecureStore; **every API response zod-parsed**.
- Skeletons not spinners; every list has a designed empty state.

## Backend contract reference (verified against `apps/api`, do not re-derive)

All under `/v1/doctor` unless noted; all require the `doctor` role.

- `GET /stats` → `{ appointmentsToday, pending, completed, prescriptionsIssued, newPatients }` (all `int`).
- `GET /appointments?date=YYYY-MM-DD` → `AppointmentOut[]` `{ id, patientName, patientAge, patientSex, photoUrl, time, status, acuity, complaint }`. `date` defaults to today server-side (the seed gives the demo doctor ≥5 for today). `status` is **already a human label** mapped server-side (`Upcoming|Arrived|In Progress|Completed`) — render it directly, do not re-map. `acuity` may be `null`.
- `GET /patients/{patientId}` → `PatientProfileOut` `{ name, age, sex, conditions[], allergies[], familyHistory[], noKnownAllergies, latestVisit, visits[], prescriptions[] }`; `latestVisit`/`visits[]` items are `{ visitedAt, summary, status }`. 404 unless the patient is booked with this doctor.
- `GET /prescriptions?status=all|active|completed` → `DoctorPrescriptionOut[]` `{ id, patientName, issuedAt, firstDrug, status }`.
- `GET /lab-reports?status=all|pending|completed` → `LabReportOut[]` `{ id, patientName, date, status }`.
- `GET /availability` / `PUT /availability` → `AvailabilityOut[]` (7 rows) `{ weekday, morning, evening, isOpen }`; PUT body is `{ days: AvailabilityOut[] }`, returns the saved week.
- `GET /profile` / `PUT /profile` → `DoctorProfileOut` `{ name, specialty, qualifications, experienceYears, clinicAddress, about, photoUrl }`; PUT body is `{ clinicAddress?, about? }` (only these two are editable).
- `GET /v1/medicines?q=` → `MedicineOut[]` `{ id, name, strength, form }`; empty `q` returns common medicines.
- `POST /v1/consultations/{id}/notes` `{ text }` → `{ id }`; `GET /v1/consultations/{id}/notes` → `NoteOut[]` `{ id, text, createdAt }`. Notes are a **private per-author** notebook (the doctor sees only notes they wrote).

---

### Task 1: Backend — expose `patientId` on queue items and appointments

The patient medical-history endpoint is keyed by `patientId`, but `QueueItemOut` and `AppointmentOut` currently expose only the **consultation** id, so the app has no id to open a patient file with. Add one additive field to each schema. RBAC is unchanged — `GET /v1/doctor/patients/{id}` still gates on `owned_by_doctor`, so exposing the id leaks nothing.

**Files:**
- Modify: `apps/api/app/schemas/consultation.py`
- Modify: `apps/api/app/schemas/appointment.py`
- Modify: `apps/api/app/services/consultation_service.py`
- Modify: `apps/api/tests/test_doctor_portal.py`

**Interfaces:**
- Produces: `QueueItemOut` gains `patientId: str`; `AppointmentOut` gains `patientId: str`. Consumed by this plan's `PatientProfileSchema` navigation (Tasks 4–5).

- [ ] **Step 1: Write the failing test**

Append to `apps/api/tests/test_doctor_portal.py` (reuse the existing `doctor_token` fixture and whatever seeded-doctor helper the file already uses; match the file's current style):

```python
def test_appointments_expose_patient_id(client, doctor_token):
    h = {"Authorization": f"Bearer {doctor_token}"}
    rows = client.get("/v1/doctor/appointments", headers=h).json()
    assert rows, "seed should give the demo doctor appointments"
    assert all(r.get("patientId") for r in rows)

def test_queue_items_expose_patient_id(client, doctor_token):
    h = {"Authorization": f"Bearer {doctor_token}"}
    rows = client.get("/v1/doctor/queue", headers=h).json()
    assert all("patientId" in r for r in rows)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd apps/api && .venv/Scripts/python -m pytest tests/test_doctor_portal.py -k patient_id -v`
Expected: FAIL — `KeyError`/assert on missing `patientId`.

- [ ] **Step 3: Add the fields**

In `apps/api/app/schemas/consultation.py`, add to `QueueItemOut` (after `id`):
```python
    patientId: str
```
In `apps/api/app/schemas/appointment.py`, add to `AppointmentOut` (after `id`):
```python
    patientId: str
```

- [ ] **Step 4: Populate them in the service**

In `apps/api/app/services/consultation_service.py`, find where `QueueItemOut(...)` and `AppointmentOut(...)` are constructed (in `doctor_queue` and `doctor_appointments`). Each builds from a row that already has the `Consultation` (which carries `patient_id`). Add `patientId=str(consult.patient_id)` (use the actual consultation/row variable name in that function) to both constructors. Do not change any other field.

- [ ] **Step 5: Run to verify it passes (and the suite stays green)**

Run: `cd apps/api && .venv/Scripts/python -m pytest tests/test_doctor_portal.py tests/test_consultations.py -v`
Expected: PASS.

- [ ] **Step 6: Mirror in shared-types + commit**

Hand-add `patientId: string;` to the `QueueItem` and `Appointment`/`AppointmentOut` interfaces in `packages/shared-types/src/types.ts` (hand-written style, per [[nadi-backend-expansion]] — do not openapi-regen). Also add it to the client `QueueItemSchema` in `apps/mobile/src/api/schemas.ts` (`patientId: z.string(),` after `id`).

```bash
git add apps/api/app/schemas/consultation.py apps/api/app/schemas/appointment.py apps/api/app/services/consultation_service.py apps/api/tests/test_doctor_portal.py packages/shared-types/src/types.ts apps/mobile/src/api/schemas.ts
git commit -m "expose patient id on queue items and appointments"
```

---

### Task 2: Doctor portal API module + zod schemas

One typed module for every v2 doctor endpoint, each response zod-parsed at the boundary.

**Files:**
- Create: `apps/mobile/src/api/doctorPortal.ts`
- Test: `apps/mobile/src/api/__tests__/doctorPortal.test.ts`

**Interfaces:**
- Consumes: `api` (Plan 01 Task 7), `AcuitySchema` (Plan 01 Task 5).
- Produces (and exports the inferred types):
  - `getDoctorStats()` → `DoctorStats`
  - `getAppointments(date?: string)` → `Appointment[]`
  - `searchMedicines(q?: string)` → `Medicine[]`
  - `getPatient(patientId: string)` → `PatientProfile`
  - `listDoctorPrescriptions(status?: 'all'|'active'|'completed')` → `DoctorPrescription[]`
  - `listLabReports(status?: 'all'|'pending'|'completed')` → `LabReport[]`
  - `getAvailability()` / `putAvailability(days: Availability[])` → `Availability[]`
  - `getDoctorProfile()` / `updateDoctorProfile(body: { clinicAddress?: string; about?: string })` → `DoctorProfile`
  - `addNote(consultationId, text)` → `{ id }`; `listNotes(consultationId)` → `Note[]`

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/api/__tests__/doctorPortal.test.ts`:
```ts
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import {
  getDoctorStats, getAppointments, searchMedicines, getPatient,
  putAvailability, updateDoctorProfile, listNotes,
} from '@/api/doctorPortal';
import { useSession } from '@/store/session';

const BASE = 'http://test.local';
process.env.EXPO_PUBLIC_API_URL = BASE;
const server = setupServer();
beforeAll(() => server.listen());
beforeEach(() => useSession.setState({ accessToken: 'a', refreshToken: 'r' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

test('getDoctorStats parses the dashboard numbers', async () => {
  server.use(http.get(`${BASE}/v1/doctor/stats`, () => HttpResponse.json(
    { appointmentsToday: 8, pending: 3, completed: 3, prescriptionsIssued: 6, newPatients: 2 })));
  expect((await getDoctorStats()).prescriptionsIssued).toBe(6);
});

test('getAppointments passes the date and parses rows with a nullable acuity', async () => {
  let seen = '';
  server.use(http.get(`${BASE}/v1/doctor/appointments`, ({ request }) => {
    seen = new URL(request.url).searchParams.get('date') ?? '';
    return HttpResponse.json([{ id: 'c1', patientId: 'p1', patientName: 'Ramesh', patientAge: 58,
      patientSex: 'M', photoUrl: 'x', time: '10:00', status: 'BOOKED', acuity: null, complaint: 'chest pain' }]);
  }));
  const rows = await getAppointments('2026-10-20');
  expect(seen).toBe('2026-10-20');
  expect(rows[0]!.acuity).toBeNull();
  expect(rows[0]!.patientId).toBe('p1');
});

test('searchMedicines parses the catalog', async () => {
  server.use(http.get(`${BASE}/v1/medicines`, () => HttpResponse.json(
    [{ id: 'm1', name: 'Paracetamol', strength: '500mg', form: 'tablet' }])));
  expect((await searchMedicines('para'))[0]!.name).toBe('Paracetamol');
});

test('getPatient parses the medical history', async () => {
  server.use(http.get(`${BASE}/v1/doctor/patients/p1`, () => HttpResponse.json({
    name: 'Ramesh', age: 58, sex: 'M', conditions: ['Diabetes'], allergies: [],
    familyHistory: ['Hypertension'], noKnownAllergies: true,
    latestVisit: { visitedAt: '2026-10-01', summary: 'Follow-up', status: 'DONE' },
    visits: [{ visitedAt: '2026-10-01', summary: 'Follow-up', status: 'DONE' }],
    prescriptions: ['Metformin 500mg'],
  })));
  const p = await getPatient('p1');
  expect(p.noKnownAllergies).toBe(true);
  expect(p.latestVisit?.summary).toBe('Follow-up');
});

test('putAvailability round-trips the week', async () => {
  const week = Array.from({ length: 7 }, (_, weekday) => (
    { weekday, morning: '09:00-13:00', evening: '17:00-20:00', isOpen: weekday < 5 }));
  server.use(http.put(`${BASE}/v1/doctor/availability`, async ({ request }) => {
    const body = (await request.json()) as { days: unknown[] };
    return HttpResponse.json(body.days);
  }));
  expect((await putAvailability(week)).length).toBe(7);
});

test('updateDoctorProfile sends only editable fields', async () => {
  server.use(http.put(`${BASE}/v1/doctor/profile`, () => HttpResponse.json({
    name: 'Dr A', specialty: 'Cardiology', qualifications: 'MBBS, MD', experienceYears: 12,
    clinicAddress: 'New addr', about: 'Updated', photoUrl: 'x' })));
  expect((await updateDoctorProfile({ clinicAddress: 'New addr' })).clinicAddress).toBe('New addr');
});

test('listNotes parses the private notebook', async () => {
  server.use(http.get(`${BASE}/v1/consultations/c1/notes`, () => HttpResponse.json(
    [{ id: 'n1', text: 'BP elevated', createdAt: '2026-10-20T10:00:00' }])));
  expect((await listNotes('c1'))[0]!.text).toBe('BP elevated');
});
```

- [ ] **Step 2: Run to verify it fails** → `npm test -- doctorPortal` FAIL (module not found).

- [ ] **Step 3: Implement**

`apps/mobile/src/api/doctorPortal.ts`:
```ts
import { z } from 'zod';
import { api } from '@/api/client';
import { AcuitySchema } from '@/api/schemas';

export const DoctorStatsSchema = z.object({
  appointmentsToday: z.number(), pending: z.number(), completed: z.number(),
  prescriptionsIssued: z.number(), newPatients: z.number(),
});
export const AppointmentSchema = z.object({
  id: z.string(), patientId: z.string(), patientName: z.string(), patientAge: z.number(),
  patientSex: z.string(), photoUrl: z.string(), time: z.string(), status: z.string(),
  acuity: AcuitySchema.nullable(), complaint: z.string(),
});
export const MedicineSchema = z.object({
  id: z.string(), name: z.string(), strength: z.string(), form: z.string(),
});
export const VisitSchema = z.object({ visitedAt: z.string(), summary: z.string(), status: z.string() });
export const PatientProfileSchema = z.object({
  name: z.string(), age: z.number(), sex: z.string(),
  conditions: z.array(z.string()), allergies: z.array(z.string()), familyHistory: z.array(z.string()),
  noKnownAllergies: z.boolean(), latestVisit: VisitSchema.nullable(),
  visits: z.array(VisitSchema), prescriptions: z.array(z.string()),
});
export const DoctorPrescriptionSchema = z.object({
  id: z.string(), patientName: z.string(), issuedAt: z.string(), firstDrug: z.string(), status: z.string(),
});
export const LabReportSchema = z.object({
  id: z.string(), patientName: z.string(), date: z.string(), status: z.string(),
});
export const AvailabilitySchema = z.object({
  weekday: z.number(), morning: z.string(), evening: z.string(), isOpen: z.boolean(),
});
export const DoctorProfileSchema = z.object({
  name: z.string(), specialty: z.string(), qualifications: z.string(), experienceYears: z.number(),
  clinicAddress: z.string(), about: z.string(), photoUrl: z.string(),
});
export const NoteSchema = z.object({ id: z.string(), text: z.string(), createdAt: z.string() });

export type DoctorStats = z.infer<typeof DoctorStatsSchema>;
export type Appointment = z.infer<typeof AppointmentSchema>;
export type Medicine = z.infer<typeof MedicineSchema>;
export type PatientProfile = z.infer<typeof PatientProfileSchema>;
export type DoctorPrescription = z.infer<typeof DoctorPrescriptionSchema>;
export type LabReport = z.infer<typeof LabReportSchema>;
export type Availability = z.infer<typeof AvailabilitySchema>;
export type DoctorProfile = z.infer<typeof DoctorProfileSchema>;
export type Note = z.infer<typeof NoteSchema>;

export const getDoctorStats = () => api.get('/v1/doctor/stats', DoctorStatsSchema);

export const getAppointments = (date?: string): Promise<Appointment[]> => {
  const q = date ? `?date=${encodeURIComponent(date)}` : '';
  return api.get(`/v1/doctor/appointments${q}`, z.array(AppointmentSchema));
};

export const searchMedicines = (q?: string): Promise<Medicine[]> => {
  const query = q && q.trim() ? `?q=${encodeURIComponent(q.trim())}` : '';
  return api.get(`/v1/medicines${query}`, z.array(MedicineSchema));
};

export const getPatient = (patientId: string) =>
  api.get(`/v1/doctor/patients/${patientId}`, PatientProfileSchema);

export const listDoctorPrescriptions = (status: 'all' | 'active' | 'completed' = 'all') =>
  api.get(`/v1/doctor/prescriptions?status=${status}`, z.array(DoctorPrescriptionSchema));

export const listLabReports = (status: 'all' | 'pending' | 'completed' = 'all') =>
  api.get(`/v1/doctor/lab-reports?status=${status}`, z.array(LabReportSchema));

export const getAvailability = () => api.get('/v1/doctor/availability', z.array(AvailabilitySchema));

export const putAvailability = (days: Availability[]) =>
  api.put('/v1/doctor/availability', { days }, z.array(AvailabilitySchema));

export const getDoctorProfile = () => api.get('/v1/doctor/profile', DoctorProfileSchema);

export const updateDoctorProfile = (body: { clinicAddress?: string; about?: string }) =>
  api.put('/v1/doctor/profile', body, DoctorProfileSchema);

export const addNote = (consultationId: string, text: string) =>
  api.post(`/v1/consultations/${consultationId}/notes`, { text }, z.object({ id: z.string() }));

export const listNotes = (consultationId: string) =>
  api.get(`/v1/consultations/${consultationId}/notes`, z.array(NoteSchema));
```

This introduces `api.put`. In `apps/mobile/src/api/client.ts`, add a `put` method mirroring `post` (same body/JSON/zod handling, `method: 'PUT'`):
```ts
  async put<T>(path: string, body: unknown, schema?: z.ZodType<T>): Promise<T> {
    const res = await request(path, {
      method: 'PUT', headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return schema ? schema.parse(data) : (data as T);
  },
```
(Add it inside the `export const api = { ... }` object, after `post`.)

- [ ] **Step 4: Run to verify it passes** → `npm test -- doctorPortal` PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/mobile/src/api/doctorPortal.ts apps/mobile/src/api/__tests__/doctorPortal.test.ts apps/mobile/src/api/client.ts
git commit -m "add doctor portal api module"
```

---

### Task 3: Dashboard home + relocate the queue

Repurpose the doctor index as a dashboard (stat tiles + navigation), move the Plan 03 queue to its own route. A reusable `StatTile` and `NavCard` carry both the dashboard and (later) the pharmacy dashboard's visual language.

**Files:**
- Create: `apps/mobile/app/(doctor)/queue.tsx` (moved Plan 03 queue)
- Modify: `apps/mobile/app/(doctor)/index.tsx` (was the queue → now the dashboard)
- Create: `apps/mobile/src/features/doctor/useDoctorStats.ts`
- Create: `apps/mobile/src/components/StatTile.tsx`, `apps/mobile/src/components/NavCard.tsx`
- Test: `apps/mobile/src/components/__tests__/StatTile.test.tsx`

**Interfaces:**
- Consumes: `getDoctorStats`, `pollInterval`.
- Produces: `useDoctorStats()` React Query (refetch 10000 ms); `StatTile({ label, value, tint? })`; `NavCard({ label, onPress, Icon })`; the dashboard screen; the queue now at `/(doctor)/queue`.

- [ ] **Step 1: Move the queue**

Create `apps/mobile/app/(doctor)/queue.tsx` with the **exact contents** of the current `apps/mobile/app/(doctor)/index.tsx` (the Plan 03 queue screen — the `DoctorQueue` default export, `useQueue`, FlashList, QueueRow). Rename the component `DoctorQueue` → `DoctorQueueScreen`. Its row `onPress` still routes to `/(doctor)/case/[cid]` — unchanged.

- [ ] **Step 2: Write the failing test**

`apps/mobile/src/components/__tests__/StatTile.test.tsx`:
```tsx
import { render, screen } from '@testing-library/react-native';
import { StatTile } from '@/components/StatTile';

test('renders a label and value', () => {
  render(<StatTile label="Prescriptions Issued" value={6} />);
  expect(screen.getByText('Prescriptions Issued')).toBeOnTheScreen();
  expect(screen.getByText('6')).toBeOnTheScreen();
});
```

- [ ] **Step 3: Run to verify it fails** → `npm test -- StatTile` FAIL.

- [ ] **Step 4: Implement the primitives + stats hook**

`apps/mobile/src/components/StatTile.tsx`:
```tsx
import { Text, View } from 'react-native';
import { Card } from '@/components/ui';
import { colors, type as t } from '@/theme/tokens';

export function StatTile({ label, value, tint }: { label: string; value: number; tint?: string }) {
  return (
    <View style={{ width: '47%' }}>
      <Card>
        <Text style={{ fontSize: t.h1, fontWeight: '800', color: tint ?? colors.navy }}>{value}</Text>
        <Text style={{ fontSize: t.xs, color: colors.textMuted }}>{label}</Text>
      </Card>
    </View>
  );
}
```

`apps/mobile/src/components/NavCard.tsx`:
```tsx
import type { ComponentType } from 'react';
import { Pressable, Text, View } from 'react-native';
import { colors, radii, spacing, type as t } from '@/theme/tokens';

type Props = { label: string; onPress: () => void; Icon: ComponentType<{ size?: number; color?: string }> };
export function NavCard({ label, onPress, Icon }: Props) {
  return (
    <Pressable onPress={onPress} style={{ width: '47%', flexDirection: 'row', alignItems: 'center',
      gap: spacing.sm, backgroundColor: colors.surface, borderRadius: radii.md, borderWidth: 1,
      borderColor: colors.border, padding: spacing.md, minHeight: 56 }}>
      <Icon size={22} color={colors.navy} />
      <Text style={{ fontSize: t.sm, color: colors.text, fontWeight: '600', flex: 1 }}>{label}</Text>
    </Pressable>
  );
}
```

`apps/mobile/src/features/doctor/useDoctorStats.ts`:
```ts
import { useQuery } from '@tanstack/react-query';
import { getDoctorStats } from '@/api/doctorPortal';
import { pollInterval } from '@/lib/polling';
export function useDoctorStats() {
  return useQuery({ queryKey: ['doctorStats'], queryFn: getDoctorStats,
    refetchInterval: () => pollInterval(true, 10000) });
}
```

- [ ] **Step 5: Build the dashboard**

Replace `apps/mobile/app/(doctor)/index.tsx` entirely:
```tsx
import { ScrollView, Text, View } from 'react-native';
import { router } from 'expo-router';
import { ListChecks, CalendarDays, FileText, FlaskConical, Clock, UserCog } from 'lucide-react-native';
import { StatTile } from '@/components/StatTile';
import { NavCard } from '@/components/NavCard';
import { Skeleton } from '@/components/ui';
import { useDoctorStats } from '@/features/doctor/useDoctorStats';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function DoctorDashboard() {
  const { data, isLoading } = useDoctorStats();
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.h2, fontWeight: '800', color: colors.navy }}>Dashboard</Text>
      {isLoading || !data ? (
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm }}>
          {[0, 1, 2, 3].map((i) => <View key={i} style={{ width: '47%' }}><Skeleton height={76} /></View>)}
        </View>
      ) : (
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm }}>
          <StatTile label="Appointments Today" value={data.appointmentsToday} />
          <StatTile label="Pending" value={data.pending} tint={colors.urgent} />
          <StatTile label="Completed" value={data.completed} tint={colors.routine} />
          <StatTile label="Prescriptions Issued" value={data.prescriptionsIssued} />
          <StatTile label="New Patients" value={data.newPatients} />
        </View>
      )}
      <Text style={{ fontSize: t.h3, fontWeight: '700', color: colors.text }}>Manage</Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm }}>
        <NavCard label="Live Queue" Icon={ListChecks} onPress={() => router.push('/(doctor)/queue')} />
        <NavCard label="Appointments" Icon={CalendarDays} onPress={() => router.push('/(doctor)/appointments')} />
        <NavCard label="Prescriptions" Icon={FileText} onPress={() => router.push('/(doctor)/prescriptions')} />
        <NavCard label="Lab Reports" Icon={FlaskConical} onPress={() => router.push('/(doctor)/lab-reports')} />
        <NavCard label="Availability" Icon={Clock} onPress={() => router.push('/(doctor)/availability')} />
        <NavCard label="Profile" Icon={UserCog} onPress={() => router.push('/(doctor)/profile')} />
      </View>
    </ScrollView>
  );
}
```

- [ ] **Step 6: Run + commit**

Run: `npm test && npm run typecheck`
```bash
git add apps/mobile/app/(doctor)/index.tsx apps/mobile/app/(doctor)/queue.tsx apps/mobile/src/features/doctor/useDoctorStats.ts apps/mobile/src/components/StatTile.tsx apps/mobile/src/components/NavCard.tsx apps/mobile/src/components/__tests__/StatTile.test.tsx
git commit -m "add doctor dashboard and relocate queue"
```

---

### Task 4: Appointments board (dated, status-grouped)

**Files:**
- Create: `apps/mobile/app/(doctor)/appointments.tsx`
- Create: `apps/mobile/src/features/doctor/useAppointments.ts`
- Create: `apps/mobile/src/components/AppointmentRow.tsx`
- Create: `apps/mobile/src/lib/dates.ts`
- Test: `apps/mobile/src/lib/__tests__/dates.test.ts`

**Interfaces:**
- Consumes: `getAppointments`, `pollInterval`.
- Produces: `isoDate(d: Date)` → `YYYY-MM-DD`; `dayChips()` → `[{ label, iso }]` for Today/Tomorrow/day-after; `useAppointments(dateIso)` (refetch 5000 ms); `AppointmentRow({ appt, onPress })` showing time, name/age/sex, the server-provided status label, and an `AcuityBadge` when `acuity` is non-null; the appointments screen with day chips and a FlashList.

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/lib/__tests__/dates.test.ts`:
```ts
import { isoDate } from '@/lib/dates';
test('isoDate formats as YYYY-MM-DD', () => {
  expect(isoDate(new Date('2026-10-20T09:30:00'))).toBe('2026-10-20');
});
```

- [ ] **Step 2: Run to verify it fails** → `npm test -- dates` FAIL.

- [ ] **Step 3: Implement the date helpers**

`apps/mobile/src/lib/dates.ts`:
```ts
export function isoDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export function dayChips(): { label: string; iso: string }[] {
  const base = new Date();
  const mk = (offset: number, label: string) => {
    const d = new Date(base);
    d.setDate(base.getDate() + offset);
    return { label, iso: isoDate(d) };
  };
  return [mk(0, 'Today'), mk(1, 'Tomorrow'), mk(2, isoDate(new Date(base.getTime() + 2 * 86400000)).slice(5))];
}
```

- [ ] **Step 4: Run to verify it passes** → `npm test -- dates` PASS.

- [ ] **Step 5: Implement the hook + row**

`apps/mobile/src/features/doctor/useAppointments.ts`:
```ts
import { useQuery } from '@tanstack/react-query';
import { getAppointments } from '@/api/doctorPortal';
import { pollInterval } from '@/lib/polling';
export function useAppointments(dateIso: string) {
  return useQuery({ queryKey: ['appointments', dateIso], queryFn: () => getAppointments(dateIso),
    refetchInterval: () => pollInterval(true, 5000) });
}
```

`apps/mobile/src/components/AppointmentRow.tsx`:
```tsx
import { Pressable, Text, View } from 'react-native';
import { AcuityBadge, Card } from '@/components/ui';
import type { Appointment } from '@/api/doctorPortal';
import { colors, spacing, type as t } from '@/theme/tokens';

export function AppointmentRow({ appt, onPress }: { appt: Appointment; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} style={{ marginBottom: spacing.sm }}>
      <Card>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.md }}>
          <Text style={{ fontSize: t.body, fontWeight: '800', color: colors.navy, width: 64 }}>{appt.time}</Text>
          <View style={{ flex: 1 }}>
            <Text style={{ fontSize: t.body, fontWeight: '700', color: colors.text }}>
              {appt.patientName}, {appt.patientAge}{appt.patientSex}
            </Text>
            <Text style={{ fontSize: t.sm, color: colors.textMuted }} numberOfLines={1}>{appt.complaint}</Text>
          </View>
          <View style={{ alignItems: 'flex-end', gap: 4 }}>
            <Text style={{ fontSize: t.xs, color: colors.navy, fontWeight: '700' }}>{appt.status}</Text>
            {appt.acuity ? <AcuityBadge acuity={appt.acuity} /> : null}
          </View>
        </View>
      </Card>
    </Pressable>
  );
}
```

- [ ] **Step 6: Build the appointments screen**

`apps/mobile/app/(doctor)/appointments.tsx`:
```tsx
import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { FlashList } from '@shopify/flash-list';
import { router } from 'expo-router';
import { EmptyState, ErrorState, Skeleton } from '@/components/ui';
import { AppointmentRow } from '@/components/AppointmentRow';
import { useAppointments } from '@/features/doctor/useAppointments';
import { dayChips } from '@/lib/dates';
import { colors, spacing, type as t } from '@/theme/tokens';

const CHIPS = dayChips();

export default function Appointments() {
  const [iso, setIso] = useState(CHIPS[0]!.iso);
  const { data, isLoading, isError, refetch } = useAppointments(iso);
  return (
    <View style={{ flex: 1 }}>
      <View style={{ flexDirection: 'row', gap: spacing.sm, padding: spacing.lg, paddingBottom: spacing.sm }}>
        {CHIPS.map((c) => (
          <Pressable key={c.iso} onPress={() => setIso(c.iso)} style={{ paddingVertical: 8, paddingHorizontal: 16,
            borderRadius: 999, backgroundColor: iso === c.iso ? colors.navy : colors.lightGrey }}>
            <Text style={{ color: iso === c.iso ? '#fff' : colors.text, fontSize: t.sm }}>{c.label}</Text>
          </Pressable>
        ))}
      </View>
      {isLoading ? (
        <View style={{ padding: spacing.lg, gap: spacing.sm }}>{[0, 1, 2].map((i) => <Skeleton key={i} height={76} />)}</View>
      ) : isError ? (
        <ErrorState message="Could not load appointments." onRetry={refetch} />
      ) : (
        <FlashList data={data ?? []} estimatedItemSize={92} keyExtractor={(a) => a.id}
          contentContainerStyle={{ padding: spacing.lg, paddingTop: 0 }}
          ListEmptyComponent={<EmptyState title="No appointments" message="Nothing booked for this day." />}
          renderItem={({ item }) => (
            <AppointmentRow appt={item} onPress={() =>
              router.push({ pathname: '/(doctor)/patient/[pid]', params: { pid: item.patientId } })} />
          )} />
      )}
    </View>
  );
}
```

- [ ] **Step 7: Run + commit**

Run: `npm test && npm run typecheck`
```bash
git add apps/mobile/app/(doctor)/appointments.tsx apps/mobile/src/features/doctor/useAppointments.ts apps/mobile/src/components/AppointmentRow.tsx apps/mobile/src/lib/dates.ts apps/mobile/src/lib/__tests__/dates.test.ts
git commit -m "add doctor appointments board"
```

---

### Task 5: Patient medical-history file + consultation notes

The patient file opened from an appointment (by `patientId`). Renders conditions / allergies ("No known allergies" when the flag is set) / family history / latest visit + history / past prescriptions. A private per-author **notes** section lets the doctor add and read their own notes — but notes are keyed by **consultation**, so the notes panel appears on the queue **case** screen (which has a consultation id), while this history screen is keyed by patient.

**Files:**
- Create: `apps/mobile/app/(doctor)/patient/[pid].tsx`
- Create: `apps/mobile/src/features/doctor/usePatient.ts`
- Create: `apps/mobile/src/features/doctor/useNotes.ts`
- Create: `apps/mobile/src/components/NotesPanel.tsx`
- Modify: `apps/mobile/app/(doctor)/case/[cid].tsx` (add the NotesPanel)
- Test: `apps/mobile/src/features/doctor/__tests__/useNotes.test.tsx`

**Interfaces:**
- Consumes: `getPatient`, `addNote`, `listNotes`.
- Produces: `usePatient(pid)` React Query; `useNotes(consultationId)` → `{ notes, add(text), pending }` (invalidates on add); `NotesPanel({ consultationId })`; the patient-history screen; the case screen gains the notes panel.

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/features/doctor/__tests__/useNotes.test.tsx`:
```tsx
import { renderHook, act, waitFor } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useNotes } from '@/features/doctor/useNotes';

jest.mock('@/api/doctorPortal', () => {
  const store: { id: string; text: string; createdAt: string }[] = [];
  return {
    listNotes: jest.fn(async () => [...store]),
    addNote: jest.fn(async (_c: string, text: string) => {
      store.push({ id: `n${store.length}`, text, createdAt: '2026-10-20T10:00:00' });
      return { id: `n${store.length - 1}` };
    }),
  };
});

const wrap = ({ children }: { children: React.ReactNode }) =>
  <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>;

test('adds a note and the list reflects it', async () => {
  const { result } = renderHook(() => useNotes('c1'), { wrapper: wrap });
  await act(async () => { await result.current.add('BP elevated'); });
  await waitFor(() => expect(result.current.notes.some((n) => n.text === 'BP elevated')).toBe(true));
});
```

- [ ] **Step 2: Run to verify it fails** → `npm test -- useNotes` FAIL.

- [ ] **Step 3: Implement the hooks**

`apps/mobile/src/features/doctor/usePatient.ts`:
```ts
import { useQuery } from '@tanstack/react-query';
import { getPatient } from '@/api/doctorPortal';
export function usePatient(pid: string) {
  return useQuery({ queryKey: ['patient', pid], queryFn: () => getPatient(pid) });
}
```

`apps/mobile/src/features/doctor/useNotes.ts`:
```ts
import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { addNote, listNotes, type Note } from '@/api/doctorPortal';
export function useNotes(consultationId: string) {
  const qc = useQueryClient();
  const [pending, setPending] = useState(false);
  const q = useQuery({ queryKey: ['notes', consultationId], queryFn: () => listNotes(consultationId) });
  const add = async (text: string) => {
    setPending(true);
    try { await addNote(consultationId, text); await qc.invalidateQueries({ queryKey: ['notes', consultationId] }); }
    finally { setPending(false); }
  };
  const notes: Note[] = q.data ?? [];
  return { notes, add, pending };
}
```

- [ ] **Step 4: Run to verify it passes** → `npm test -- useNotes` PASS.

- [ ] **Step 5: Build the NotesPanel + patient-history screen**

`apps/mobile/src/components/NotesPanel.tsx`:
```tsx
import { useState } from 'react';
import { Text, View } from 'react-native';
import { Button, Card, Input } from '@/components/ui';
import { useNotes } from '@/features/doctor/useNotes';
import { colors, spacing, type as t } from '@/theme/tokens';

export function NotesPanel({ consultationId }: { consultationId: string }) {
  const { notes, add, pending } = useNotes(consultationId);
  const [text, setText] = useState('');
  const save = async () => { if (!text.trim()) return; await add(text.trim()); setText(''); };
  return (
    <Card>
      <Text style={{ fontSize: t.sm, color: colors.navy, fontWeight: '800' }}>MY NOTES</Text>
      <Text style={{ fontSize: t.xs, color: colors.textMuted, marginBottom: spacing.sm }}>Private to you.</Text>
      {notes.length === 0 ? (
        <Text style={{ fontSize: t.sm, color: colors.textMuted }}>No notes yet.</Text>
      ) : notes.map((n) => (
        <Text key={n.id} style={{ fontSize: t.sm, color: colors.text, marginBottom: 4 }}>• {n.text}</Text>
      ))}
      <View style={{ height: spacing.sm }} />
      <Input value={text} onChangeText={setText} multiline placeholder="Add a private note…" />
      <View style={{ height: spacing.sm }} />
      <Button title="Save note" color={colors.navy} loading={pending} disabled={!text.trim()} onPress={save} />
    </Card>
  );
}
```

`apps/mobile/app/(doctor)/patient/[pid].tsx`:
```tsx
import { ScrollView, Text, View } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { Card, Skeleton, ErrorState } from '@/components/ui';
import { usePatient } from '@/features/doctor/usePatient';
import { colors, spacing, type as t } from '@/theme/tokens';

function Section({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  return (
    <Card>
      <Text style={{ fontSize: t.sm, color: colors.textMuted, marginBottom: spacing.xs }}>{title}</Text>
      {items.length === 0 ? <Text style={{ fontSize: t.sm, color: colors.text }}>{empty}</Text>
        : items.map((it, i) => <Text key={i} style={{ fontSize: t.sm, color: colors.text }}>• {it}</Text>)}
    </Card>
  );
}

export default function PatientFile() {
  const { pid } = useLocalSearchParams<{ pid: string }>();
  const { data, isLoading, isError, refetch } = usePatient(pid!);
  if (isLoading) return <View style={{ padding: spacing.lg, gap: spacing.md }}><Skeleton height={28} /><Skeleton height={120} /></View>;
  if (isError || !data) return <ErrorState message="Could not load this patient." onRetry={refetch} />;
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.h2, fontWeight: '700', color: colors.text }}>{data.name}, {data.age}{data.sex}</Text>
      <Section title="Conditions" items={data.conditions} empty="None recorded" />
      <Section title="Allergies" items={data.allergies} empty={data.noKnownAllergies ? 'No known allergies' : 'None recorded'} />
      <Section title="Family history" items={data.familyHistory} empty="None recorded" />
      <Card>
        <Text style={{ fontSize: t.sm, color: colors.textMuted, marginBottom: spacing.xs }}>Latest visit</Text>
        {data.latestVisit ? (
          <Text style={{ fontSize: t.sm, color: colors.text }}>
            {data.latestVisit.visitedAt} — {data.latestVisit.summary} ({data.latestVisit.status})
          </Text>
        ) : <Text style={{ fontSize: t.sm, color: colors.text }}>No visits yet</Text>}
      </Card>
      <Section title="Past prescriptions" items={data.prescriptions} empty="None issued" />
    </ScrollView>
  );
}
```

- [ ] **Step 6: Add the notes panel to the case screen**

In `apps/mobile/app/(doctor)/case/[cid].tsx` (Plan 03 Task 3), import the panel and render it below the labs card, above the action buttons:
```tsx
import { NotesPanel } from '@/components/NotesPanel';
```
Insert (after the labs `Card` block, before the `Start consultation` button):
```tsx
      <NotesPanel consultationId={item.id} />
```

- [ ] **Step 7: Run + commit**

Run: `npm test && npm run typecheck`
```bash
git add apps/mobile/app/(doctor)/patient apps/mobile/app/(doctor)/case apps/mobile/src/features/doctor/usePatient.ts apps/mobile/src/features/doctor/useNotes.ts apps/mobile/src/components/NotesPanel.tsx apps/mobile/src/features/doctor/__tests__/useNotes.test.tsx
git commit -m "add doctor patient file and notes panel"
```

---

### Task 6: Medicine search in the prescription form

Enhance the Plan 03 prescription form so the drug field autocompletes from the real catalog (`GET /v1/medicines?q=`), filling drug + strength on pick. Free text still allowed (so the doctor is never blocked by an incomplete catalog).

**Files:**
- Create: `apps/mobile/src/components/MedicineAutocomplete.tsx`
- Create: `apps/mobile/src/features/doctor/useMedicineSearch.ts`
- Modify: `apps/mobile/app/(doctor)/prescribe/[cid].tsx` (use the autocomplete for the drug field)
- Test: `apps/mobile/src/features/doctor/__tests__/useMedicineSearch.test.tsx`

**Interfaces:**
- Consumes: `searchMedicines`.
- Produces: `useMedicineSearch(q)` React Query (enabled whenever mounted; `q` empty returns common medicines); `MedicineAutocomplete({ value, onChangeText, onPick })` — a text input with a result dropdown; picking calls `onPick({ name, strength })`.

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/features/doctor/__tests__/useMedicineSearch.test.tsx`:
```tsx
import { renderHook, waitFor } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useMedicineSearch } from '@/features/doctor/useMedicineSearch';

jest.mock('@/api/doctorPortal', () => ({
  searchMedicines: jest.fn(async (q?: string) =>
    (q === 'amox' ? [{ id: 'm2', name: 'Amoxicillin', strength: '500mg', form: 'capsule' }] : [])),
}));

const wrap = ({ children }: { children: React.ReactNode }) =>
  <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>;

test('returns matches for the query', async () => {
  const { result } = renderHook(() => useMedicineSearch('amox'), { wrapper: wrap });
  await waitFor(() => expect(result.current.data?.[0]?.name).toBe('Amoxicillin'));
});
```

- [ ] **Step 2: Run to verify it fails** → `npm test -- useMedicineSearch` FAIL.

- [ ] **Step 3: Implement the hook + component**

`apps/mobile/src/features/doctor/useMedicineSearch.ts`:
```ts
import { useQuery } from '@tanstack/react-query';
import { searchMedicines } from '@/api/doctorPortal';
export function useMedicineSearch(q: string) {
  return useQuery({ queryKey: ['medicines', q], queryFn: () => searchMedicines(q), staleTime: 60000 });
}
```

`apps/mobile/src/components/MedicineAutocomplete.tsx`:
```tsx
import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { Input } from '@/components/ui';
import { useMedicineSearch } from '@/features/doctor/useMedicineSearch';
import { colors, radii, spacing, type as t } from '@/theme/tokens';

type Props = {
  value: string;
  onChangeText: (v: string) => void;
  onPick: (m: { name: string; strength: string }) => void;
};
export function MedicineAutocomplete({ value, onChangeText, onPick }: Props) {
  const [focused, setFocused] = useState(false);
  const { data } = useMedicineSearch(value);
  const show = focused && (data?.length ?? 0) > 0;
  return (
    <View>
      <Input value={value} placeholder="Drug (search catalog)"
        onChangeText={(v) => { onChangeText(v); setFocused(true); }} />
      {show ? (
        <View style={{ borderWidth: 1, borderColor: colors.border, borderRadius: radii.sm, marginTop: 4 }}>
          {(data ?? []).slice(0, 6).map((m) => (
            <Pressable key={m.id} onPress={() => { onPick({ name: m.name, strength: m.strength }); setFocused(false); }}
              style={{ padding: spacing.sm, borderBottomWidth: 1, borderBottomColor: colors.border }}>
              <Text style={{ fontSize: t.sm, color: colors.text }}>{m.name} {m.strength} · {m.form}</Text>
            </Pressable>
          ))}
        </View>
      ) : null}
    </View>
  );
}
```

- [ ] **Step 4: Run to verify it passes** → `npm test -- useMedicineSearch` PASS.

- [ ] **Step 5: Wire the autocomplete into the prescribe form**

In `apps/mobile/app/(doctor)/prescribe/[cid].tsx` (Plan 03 Task 4), replace the first `<Input ... placeholder="Drug" />` with the autocomplete, which also fills the strength field on pick:
```tsx
import { MedicineAutocomplete } from '@/components/MedicineAutocomplete';
```
Replace the drug `Input` line inside the row with:
```tsx
          <MedicineAutocomplete value={l.drug}
            onChangeText={(v) => patch(i, { drug: v })}
            onPick={(m) => patch(i, { drug: m.name, strength: m.strength })} />
```
Leave the remaining fields (strength, frequency, days) as plain inputs. The `valid` gate and submit are unchanged.

- [ ] **Step 6: Run + commit**

Run: `npm test && npm run typecheck`
```bash
git add apps/mobile/src/components/MedicineAutocomplete.tsx apps/mobile/src/features/doctor/useMedicineSearch.ts apps/mobile/app/(doctor)/prescribe apps/mobile/src/features/doctor/__tests__/useMedicineSearch.test.tsx
git commit -m "add medicine search to prescription form"
```

---

### Task 7: Prescriptions list + Lab reports list

Two near-identical filtered list screens reachable from the dashboard.

**Files:**
- Create: `apps/mobile/app/(doctor)/prescriptions.tsx`
- Create: `apps/mobile/app/(doctor)/lab-reports.tsx`
- Create: `apps/mobile/src/features/doctor/useDoctorLists.ts`
- Create: `apps/mobile/src/components/FilterChips.tsx`
- Test: `apps/mobile/src/components/__tests__/FilterChips.test.tsx`

**Interfaces:**
- Consumes: `listDoctorPrescriptions`, `listLabReports`.
- Produces: `FilterChips({ options, value, onChange })` (reused by the pharmacy board in Plan 06); `useDoctorPrescriptions(status)` and `useLabReports(status)` React Query hooks; the two list screens with chips + FlashList + empty state.

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/components/__tests__/FilterChips.test.tsx`:
```tsx
import { fireEvent, render, screen } from '@testing-library/react-native';
import { FilterChips } from '@/components/FilterChips';

test('calls onChange with the chosen value', () => {
  const onChange = jest.fn();
  render(<FilterChips options={[{ label: 'All', value: 'all' }, { label: 'Active', value: 'active' }]}
    value="all" onChange={onChange} />);
  fireEvent.press(screen.getByText('Active'));
  expect(onChange).toHaveBeenCalledWith('active');
});
```

- [ ] **Step 2: Run to verify it fails** → `npm test -- FilterChips` FAIL.

- [ ] **Step 3: Implement FilterChips + the list hooks**

`apps/mobile/src/components/FilterChips.tsx`:
```tsx
import { Pressable, ScrollView, Text } from 'react-native';
import { colors, spacing, type as t } from '@/theme/tokens';

type Option = { label: string; value: string };
export function FilterChips({ options, value, onChange }:
  { options: Option[]; value: string; onChange: (v: string) => void }) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false}
      contentContainerStyle={{ gap: spacing.sm, paddingHorizontal: spacing.lg }}>
      {options.map((o) => (
        <Pressable key={o.value} onPress={() => onChange(o.value)} style={{ paddingVertical: 8, paddingHorizontal: 16,
          borderRadius: 999, backgroundColor: value === o.value ? colors.navy : colors.lightGrey }}>
          <Text style={{ color: value === o.value ? '#fff' : colors.text, fontSize: t.sm }}>{o.label}</Text>
        </Pressable>
      ))}
    </ScrollView>
  );
}
```

`apps/mobile/src/features/doctor/useDoctorLists.ts`:
```ts
import { useQuery } from '@tanstack/react-query';
import { listDoctorPrescriptions, listLabReports } from '@/api/doctorPortal';

export function useDoctorPrescriptions(status: 'all' | 'active' | 'completed') {
  return useQuery({ queryKey: ['doctorPrescriptions', status], queryFn: () => listDoctorPrescriptions(status) });
}
export function useLabReports(status: 'all' | 'pending' | 'completed') {
  return useQuery({ queryKey: ['labReports', status], queryFn: () => listLabReports(status) });
}
```

- [ ] **Step 4: Run to verify it passes** → `npm test -- FilterChips` PASS.

- [ ] **Step 5: Build the two screens**

`apps/mobile/app/(doctor)/prescriptions.tsx`:
```tsx
import { useState } from 'react';
import { Text, View } from 'react-native';
import { FlashList } from '@shopify/flash-list';
import { Card, EmptyState, ErrorState, Skeleton } from '@/components/ui';
import { FilterChips } from '@/components/FilterChips';
import { useDoctorPrescriptions } from '@/features/doctor/useDoctorLists';
import { colors, spacing, type as t } from '@/theme/tokens';

const OPTS = [{ label: 'All', value: 'all' }, { label: 'Active', value: 'active' }, { label: 'Completed', value: 'completed' }];

export default function Prescriptions() {
  const [status, setStatus] = useState<'all' | 'active' | 'completed'>('all');
  const { data, isLoading, isError, refetch } = useDoctorPrescriptions(status);
  return (
    <View style={{ flex: 1, paddingTop: spacing.lg, gap: spacing.sm }}>
      <FilterChips options={OPTS} value={status} onChange={(v) => setStatus(v as typeof status)} />
      {isLoading ? (
        <View style={{ padding: spacing.lg, gap: spacing.sm }}>{[0, 1, 2].map((i) => <Skeleton key={i} height={64} />)}</View>
      ) : isError ? <ErrorState message="Could not load prescriptions." onRetry={refetch} /> : (
        <FlashList data={data ?? []} estimatedItemSize={76} keyExtractor={(p) => p.id}
          contentContainerStyle={{ padding: spacing.lg }}
          ListEmptyComponent={<EmptyState title="No prescriptions" message="Issued prescriptions appear here." />}
          renderItem={({ item }) => (
            <View style={{ marginBottom: spacing.sm }}><Card>
              <Text style={{ fontSize: t.body, fontWeight: '700', color: colors.text }}>{item.patientName}</Text>
              <Text style={{ fontSize: t.sm, color: colors.textMuted }}>{item.firstDrug} · {item.issuedAt}</Text>
              <Text style={{ fontSize: t.xs, color: colors.navy, fontWeight: '700' }}>{item.status}</Text>
            </Card></View>
          )} />
      )}
    </View>
  );
}
```

`apps/mobile/app/(doctor)/lab-reports.tsx` — identical structure, different hook/fields/options:
```tsx
import { useState } from 'react';
import { Text, View } from 'react-native';
import { FlashList } from '@shopify/flash-list';
import { Card, EmptyState, ErrorState, Skeleton } from '@/components/ui';
import { FilterChips } from '@/components/FilterChips';
import { useLabReports } from '@/features/doctor/useDoctorLists';
import { colors, spacing, type as t } from '@/theme/tokens';

const OPTS = [{ label: 'All', value: 'all' }, { label: 'Pending', value: 'pending' }, { label: 'Completed', value: 'completed' }];

export default function LabReports() {
  const [status, setStatus] = useState<'all' | 'pending' | 'completed'>('all');
  const { data, isLoading, isError, refetch } = useLabReports(status);
  return (
    <View style={{ flex: 1, paddingTop: spacing.lg, gap: spacing.sm }}>
      <FilterChips options={OPTS} value={status} onChange={(v) => setStatus(v as typeof status)} />
      {isLoading ? (
        <View style={{ padding: spacing.lg, gap: spacing.sm }}>{[0, 1, 2].map((i) => <Skeleton key={i} height={64} />)}</View>
      ) : isError ? <ErrorState message="Could not load lab reports." onRetry={refetch} /> : (
        <FlashList data={data ?? []} estimatedItemSize={76} keyExtractor={(r) => r.id}
          contentContainerStyle={{ padding: spacing.lg }}
          ListEmptyComponent={<EmptyState title="No lab reports" message="Uploaded reports appear here." />}
          renderItem={({ item }) => (
            <View style={{ marginBottom: spacing.sm }}><Card>
              <Text style={{ fontSize: t.body, fontWeight: '700', color: colors.text }}>{item.patientName}</Text>
              <Text style={{ fontSize: t.sm, color: colors.textMuted }}>{item.date}</Text>
              <Text style={{ fontSize: t.xs, color: colors.navy, fontWeight: '700' }}>{item.status}</Text>
            </Card></View>
          )} />
      )}
    </View>
  );
}
```

- [ ] **Step 6: Run + commit**

Run: `npm test && npm run typecheck`
```bash
git add apps/mobile/app/(doctor)/prescriptions.tsx apps/mobile/app/(doctor)/lab-reports.tsx apps/mobile/src/features/doctor/useDoctorLists.ts apps/mobile/src/components/FilterChips.tsx apps/mobile/src/components/__tests__/FilterChips.test.tsx
git commit -m "add doctor prescriptions and lab reports lists"
```

---

### Task 8: Availability editor + Profile

The last two dashboard sections. Availability is 7 editable weekday rows (open toggle + morning/evening strings); profile shows the read-only identity fields and edits only `clinicAddress` + `about`.

**Files:**
- Create: `apps/mobile/app/(doctor)/availability.tsx`
- Create: `apps/mobile/app/(doctor)/profile.tsx`
- Create: `apps/mobile/src/features/doctor/useAvailability.ts`
- Create: `apps/mobile/src/features/doctor/useDoctorProfile.ts`
- Test: `apps/mobile/src/features/doctor/__tests__/useAvailability.test.tsx`

**Interfaces:**
- Consumes: `getAvailability`, `putAvailability`, `getDoctorProfile`, `updateDoctorProfile`.
- Produces: `useAvailability()` → `{ week, isLoading, toggle(weekday), setField(weekday, key, value), save(), saving }`; `useDoctorProfile()` → React Query + `save({ clinicAddress, about })`; the two screens.

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/features/doctor/__tests__/useAvailability.test.tsx`:
```tsx
import { renderHook, act, waitFor } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAvailability } from '@/features/doctor/useAvailability';

const week = Array.from({ length: 7 }, (_, weekday) =>
  ({ weekday, morning: '09:00-13:00', evening: '17:00-20:00', isOpen: weekday < 5 }));
jest.mock('@/api/doctorPortal', () => ({
  getAvailability: jest.fn(async () => week),
  putAvailability: jest.fn(async (days: unknown) => days),
}));

const wrap = ({ children }: { children: React.ReactNode }) =>
  <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>;

test('toggle flips a day open flag', async () => {
  const { result } = renderHook(() => useAvailability(), { wrapper: wrap });
  await waitFor(() => expect(result.current.week.length).toBe(7));
  act(() => { result.current.toggle(5); });
  expect(result.current.week[5]!.isOpen).toBe(true);
});
```

- [ ] **Step 2: Run to verify it fails** → `npm test -- useAvailability` FAIL.

- [ ] **Step 3: Implement the hooks**

`apps/mobile/src/features/doctor/useAvailability.ts`:
```ts
import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getAvailability, putAvailability, type Availability } from '@/api/doctorPortal';

export function useAvailability() {
  const q = useQuery({ queryKey: ['availability'], queryFn: getAvailability });
  const [week, setWeek] = useState<Availability[]>([]);
  const [saving, setSaving] = useState(false);
  useEffect(() => { if (q.data) setWeek(q.data); }, [q.data]);
  const toggle = (weekday: number) =>
    setWeek((w) => w.map((d) => (d.weekday === weekday ? { ...d, isOpen: !d.isOpen } : d)));
  const setField = (weekday: number, key: 'morning' | 'evening', value: string) =>
    setWeek((w) => w.map((d) => (d.weekday === weekday ? { ...d, [key]: value } : d)));
  const save = async () => { setSaving(true); try { await putAvailability(week); } finally { setSaving(false); } };
  return { week, isLoading: q.isLoading, toggle, setField, save, saving };
}
```

`apps/mobile/src/features/doctor/useDoctorProfile.ts`:
```ts
import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getDoctorProfile, updateDoctorProfile } from '@/api/doctorPortal';
export function useDoctorProfile() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ['doctorProfile'], queryFn: getDoctorProfile });
  const [saving, setSaving] = useState(false);
  const save = async (body: { clinicAddress?: string; about?: string }) => {
    setSaving(true);
    try { await updateDoctorProfile(body); await qc.invalidateQueries({ queryKey: ['doctorProfile'] }); }
    finally { setSaving(false); }
  };
  return { profile: q.data, isLoading: q.isLoading, save, saving };
}
```

- [ ] **Step 4: Run to verify it passes** → `npm test -- useAvailability` PASS.

- [ ] **Step 5: Build the two screens**

`apps/mobile/app/(doctor)/availability.tsx`:
```tsx
import { ScrollView, Switch, Text, View } from 'react-native';
import { router } from 'expo-router';
import { Button, Card, Input, Skeleton } from '@/components/ui';
import { useAvailability } from '@/features/doctor/useAvailability';
import { colors, spacing, type as t } from '@/theme/tokens';

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export default function AvailabilityScreen() {
  const { week, isLoading, toggle, setField, save, saving } = useAvailability();
  if (isLoading) return <View style={{ padding: spacing.lg, gap: spacing.sm }}>{[0, 1, 2].map((i) => <Skeleton key={i} height={88} />)}</View>;
  const save2 = async () => { await save(); router.back(); };
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.h2, fontWeight: '700', color: colors.text }}>Availability</Text>
      {week.map((d) => (
        <Card key={d.weekday}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text style={{ fontSize: t.body, fontWeight: '700', color: colors.text }}>{DAYS[d.weekday] ?? `Day ${d.weekday}`}</Text>
            <Switch value={d.isOpen} onValueChange={() => toggle(d.weekday)} />
          </View>
          {d.isOpen ? (
            <>
              <Input value={d.morning} onChangeText={(v) => setField(d.weekday, 'morning', v)} placeholder="Morning e.g. 09:00-13:00" />
              <View style={{ height: spacing.sm }} />
              <Input value={d.evening} onChangeText={(v) => setField(d.weekday, 'evening', v)} placeholder="Evening e.g. 17:00-20:00" />
            </>
          ) : null}
        </Card>
      ))}
      <Button title="Save availability" color={colors.navy} loading={saving} onPress={save2} />
    </ScrollView>
  );
}
```

`apps/mobile/app/(doctor)/profile.tsx`:
```tsx
import { useEffect, useState } from 'react';
import { ScrollView, Text } from 'react-native';
import { Button, Card, Input, Skeleton } from '@/components/ui';
import { useDoctorProfile } from '@/features/doctor/useDoctorProfile';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function ProfileScreen() {
  const { profile, isLoading, save, saving } = useDoctorProfile();
  const [clinic, setClinic] = useState('');
  const [about, setAbout] = useState('');
  useEffect(() => { if (profile) { setClinic(profile.clinicAddress); setAbout(profile.about); } }, [profile]);
  if (isLoading || !profile) return <Skeleton height={200} />;
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.h2, fontWeight: '700', color: colors.text }}>{profile.name}</Text>
      <Card>
        <Text style={{ fontSize: t.sm, color: colors.textMuted }}>{profile.specialty} · {profile.qualifications}</Text>
        <Text style={{ fontSize: t.sm, color: colors.text }}>{profile.experienceYears} years experience</Text>
      </Card>
      <Text style={{ fontSize: t.sm, color: colors.textMuted }}>Clinic address</Text>
      <Input value={clinic} onChangeText={setClinic} multiline placeholder="Clinic address" />
      <Text style={{ fontSize: t.sm, color: colors.textMuted }}>About</Text>
      <Input value={about} onChangeText={setAbout} multiline placeholder="About you" />
      <Button title="Save profile" color={colors.navy} loading={saving}
        onPress={() => save({ clinicAddress: clinic, about })} />
    </ScrollView>
  );
}
```

- [ ] **Step 6: Run + commit**

Run: `npm test && npm run typecheck`
```bash
git add apps/mobile/app/(doctor)/availability.tsx apps/mobile/app/(doctor)/profile.tsx apps/mobile/src/features/doctor/useAvailability.ts apps/mobile/src/features/doctor/useDoctorProfile.ts apps/mobile/src/features/doctor/__tests__/useAvailability.test.tsx
git commit -m "add doctor availability editor and profile"
```

---

## Verification (end of Plan 05)

- `cd apps/mobile && npm test && npm run typecheck` — green.
- `cd apps/api && .venv/Scripts/python -m pytest` — green (Task 1 change).
- Device, logged in as the seeded demo doctor `+915000000001`:
  - Dashboard shows real seeded numbers (Appointments Today, Prescriptions Issued ≈ 6, etc.).
  - Appointments board loads 8 seeded appointments across statuses; day chips switch the date.
  - Tapping an appointment opens the patient file with conditions / allergies ("No known allergies" where applicable) / family history / latest visit / past prescriptions.
  - The queue case screen shows the private notes panel; adding a note persists and reloads; the patient never sees it (private per-author).
  - Prescribing: the drug field autocompletes from the catalog and fills strength on pick.
  - Prescriptions and Lab Reports lists filter by status.
  - Availability loads the Mon–Fri seeded week, edits save and round-trip; Profile edits clinic address + about and persists.

**Next plan:** `06-pharmacy-portal` — dashboard stats, the orders lifecycle board, and the order status-transition detail.

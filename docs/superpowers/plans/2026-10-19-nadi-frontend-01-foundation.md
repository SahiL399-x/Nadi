# NADI Frontend — Plan 01: Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the `apps/mobile/` Expo app skeleton — scaffold, theme, typed API client, contract validation, session + role-based routing, OTP auth, and UI primitives — so a user can log in as any of the three roles and land on a themed, empty portal shell.

**Architecture:** Expo / React Native (expo-router) talking to the existing FastAPI backend over LAN. Server data via React Query (polling, no websockets); session via zustand + expo-secure-store; every API response validated at the boundary with zod. Animations/gestures run on the UI thread (Reanimated) from task one so performance is structural, not retrofitted.

**Tech Stack:** Expo SDK 53+, expo-router, NativeWind v4, zustand, @tanstack/react-query, zod, react-native-reanimated, react-native-gesture-handler, expo-secure-store, expo-network, expo-image; testing with jest-expo, @testing-library/react-native, and msw.

## Global Constraints

- TypeScript **strict**; no `any`, no `@ts-ignore` (ProjectPlan §12).
- Functional components with hooks only; components **under 150 lines** — split when longer (§12).
- **No business logic in route/screen files** — logic lives in `src/lib/` and the store (§12).
- **No inline styles and no hard-coded hex in components** — NativeWind classes or `src/theme/tokens.ts` values only (§12).
- Baseline viewport **360×640 dp**; minimum tap target **48×48 dp**; primary buttons **56 dp** tall, full width (§12).
- Body text never below **15**; type scale 30/24/20/17/15/13 (§12).
- Acuity is always a coloured **badge + text label**, never colour alone (colour-blind-safe) (§12, spec §4).
- **No AI/tool attribution anywhere** — no "generated with", no co-author trailers, no AI-signposting comments; commit messages short, imperative, lowercase (ProjectPlan §14.11).
- **The system routes, it does not diagnose** — no copy/field implies a diagnosis (§14.1).
- **Strictly $0 / no billing account** — every dependency free; no map/AI key anywhere (spec §4).
- API base URL is a single config value `EXPO_PUBLIC_API_URL`; access token in memory, refresh token in `expo-secure-store` (spec §3/§4).
- Every async view uses a **skeleton, not a spinner**; every list has a designed **empty state** (§12).
- Contract shapes mirror `@nadi/shared-types`; **every API response is parsed with zod** at the client boundary (spec §4).

---

### Task 1: Backend — expose doctor coordinates (`lat`/`lng`)

The map (Plan 02) needs per-doctor coordinates. `DoctorOut` currently returns only `distanceKm`. Add two additive, backward-compatible fields sourced from the existing `Doctor.location` PostGIS point (`POINT(lng lat)` → `ST_X`=lng, `ST_Y`=lat). Backend-only task; no mobile code yet.

**Files:**
- Modify: `apps/api/app/schemas/doctor.py`
- Modify: `apps/api/app/services/doctor_service.py`
- Modify: `apps/api/tests/test_doctors.py`

**Interfaces:**
- Produces: `DoctorOut` gains `lat: float`, `lng: float`. The `@nadi/shared-types` `Doctor` interface gains `lat: number; lng: number` after regen. Plan 02's zod `DoctorSchema` relies on these.

- [ ] **Step 1: Write the failing test**

Add to `apps/api/tests/test_doctors.py`:

```python
def test_search_returns_coordinates(client, db):
    _make_doctor(db, "Dr Geo", "Dermatology", 19.99, 73.79, 300)
    r = client.get("/v1/doctors", params={"specialty": "Dermatology",
                                          "lat": 19.9975, "lng": 73.7898, "radiusKm": 100})
    assert r.status_code == 200
    doc = r.json()[0]
    assert round(doc["lat"], 2) == 19.99
    assert round(doc["lng"], 2) == 73.79
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && .venv/Scripts/python -m pytest tests/test_doctors.py::test_search_returns_coordinates -v`
Expected: FAIL — `KeyError: 'lat'` (field not in response).

- [ ] **Step 3: Add the fields to the schema**

In `apps/api/app/schemas/doctor.py`, add to `DoctorOut` (after `distanceKm`):

```python
    lat: float
    lng: float
```

- [ ] **Step 4: Populate them in the service**

In `apps/api/app/services/doctor_service.py`:

Change `_to_out`'s signature and body to accept coordinates:

```python
def _to_out(doctor: Doctor, name: str, distance_km: float, lat: float, lng: float) -> DoctorOut:
    return DoctorOut(
        id=str(doctor.user_id), name=name, specialty=doctor.specialty,
        qualifications=doctor.qualifications, experienceYears=doctor.experience_years,
        distanceKm=round(distance_km, 1), lat=lat, lng=lng, feeInr=doctor.fee_inr,
        rating=doctor.rating, reviewCount=doctor.review_count, languages=list(doctor.languages),
        nextSlot=_SLOTS[0], photoUrl=doctor.photo_url, availableSlots=_SLOTS,
    )
```

Update `search` to select and pass coordinates:

```python
def search(db: Session, specialty: str | None, lat: float, lng: float,
           radius_km: float, lang: str | None) -> list[DoctorOut]:
    pt = _point(lat, lng)
    dist = ST_Distance(Doctor.location, pt)
    stmt = select(Doctor, User.name, dist,
                  func.ST_Y(func.cast(Doctor.location, type_=None)),
                  func.ST_X(func.cast(Doctor.location, type_=None))).join(User, User.id == Doctor.user_id)
    stmt = stmt.where(ST_DWithin(Doctor.location, pt, radius_km * 1000))
    if specialty:
        stmt = stmt.where(Doctor.specialty == specialty)
    if lang:
        stmt = stmt.where(Doctor.languages.any(_LANG_NAMES.get(lang, lang)))
    stmt = stmt.order_by(dist.asc())
    rows = db.execute(stmt).all()
    return [_to_out(d, name, d_m / 1000.0, d_lat, d_lng)
            for (d, name, d_m, d_lat, d_lng) in rows]
```

Note: `ST_Y`/`ST_X` take the geometry directly — if the cast wrapper errors on your PostGIS/geoalchemy2 version, use `func.ST_Y(Doctor.location)` and `func.ST_X(Doctor.location)` directly. Update `get` similarly, passing `doctor` coordinates via a `select(... func.ST_Y(Doctor.location), func.ST_X(Doctor.location))` and `_to_out(doctor, name, 0.0, d_lat, d_lng)`.

- [ ] **Step 5: Run test to verify it passes (and the suite stays green)**

Run: `cd apps/api && .venv/Scripts/python -m pytest tests/test_doctors.py -v`
Expected: PASS, including `test_search_orders_by_distance`.

- [ ] **Step 6: Regenerate shared types**

With the API running (`docker compose -f infra/docker-compose.yml up -d`):
Run: `cd packages/shared-types && npm run gen`
Confirm `src/types.ts` `Doctor` now includes `lat` and `lng`. If the hand-written `types.ts` is not openapi-generated in your tree, hand-add `lat: number; lng: number;` to the `Doctor` interface.

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/schemas/doctor.py apps/api/app/services/doctor_service.py apps/api/tests/test_doctors.py packages/shared-types/src/types.ts
git commit -m "expose doctor lat/lng in search results"
```

---

### Task 2: Scaffold the Expo app

**Files:**
- Create: `apps/mobile/` (Expo project)
- Create: `apps/mobile/app/index.tsx`
- Create: `apps/mobile/tsconfig.json`
- Create: `apps/mobile/jest.config.js`, `apps/mobile/jest.setup.ts`
- Create: `apps/mobile/.env` (gitignored), `apps/mobile/.env.example`
- Create: `apps/mobile/__tests__/smoke.test.tsx`

**Interfaces:**
- Produces: a runnable Expo app with a passing test harness. Path alias `@/*` → `apps/mobile/src/*` and `@nadi/shared-types` → `../../packages/shared-types/src/types.ts` (type-only).

- [ ] **Step 1: Create the app**

Run from repo root:
```bash
npx create-expo-app@latest apps/mobile --template blank-typescript
cd apps/mobile
npx expo install expo-router react-native-safe-area-context react-native-screens expo-linking expo-constants expo-status-bar
```

- [ ] **Step 2: Switch to expo-router entry**

In `apps/mobile/package.json` set `"main": "expo-router/entry"`. Add to the `expo` config in `app.json`: `"scheme": "nadi"`. Delete the template `App.tsx`. Create `apps/mobile/app/_layout.tsx`:

```tsx
import { Stack } from 'expo-router';
export default function RootLayout() {
  return <Stack screenOptions={{ headerShown: false }} />;
}
```

Create `apps/mobile/app/index.tsx`:

```tsx
import { Text, View } from 'react-native';
export default function Index() {
  return (
    <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
      <Text>NADI</Text>
    </View>
  );
}
```

- [ ] **Step 3: Configure strict TypeScript + path aliases**

`apps/mobile/tsconfig.json`:

```json
{
  "extends": "expo/tsconfig.base",
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"],
      "@nadi/shared-types": ["../../packages/shared-types/src/types.ts"]
    }
  },
  "include": ["**/*.ts", "**/*.tsx", ".expo/types/**/*.ts", "expo-env.d.ts"]
}
```

- [ ] **Step 4: Set up the test harness**

```bash
npx expo install -- --save-dev jest-expo jest @testing-library/react-native @types/jest msw
```

`apps/mobile/jest.config.js`:

```js
module.exports = {
  preset: 'jest-expo',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  transformIgnorePatterns: [
    'node_modules/(?!((jest-)?react-native|@react-native(-community)?|expo(nent)?|@expo(nent)?/.*|@expo-google-fonts/.*|react-navigation|@react-navigation/.*|@unimodules/.*|unimodules|sentry-expo|native-base|react-native-svg|nativewind|react-native-css-interop))',
  ],
};
```

`apps/mobile/jest.setup.ts`:

```ts
import '@testing-library/react-native/extend-expect';
```

Add to `package.json` scripts: `"test": "jest"`, `"typecheck": "tsc --noEmit"`.

- [ ] **Step 5: Environment config**

`apps/mobile/.env.example`:
```
EXPO_PUBLIC_API_URL=http://192.168.1.10:8000
```
Copy to `.env` with your laptop's LAN IP. Add `.env` to `apps/mobile/.gitignore`.

- [ ] **Step 6: Write and run the smoke test**

`apps/mobile/__tests__/smoke.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react-native';
import Index from '../app/index';

test('renders the app name', () => {
  render(<Index />);
  expect(screen.getByText('NADI')).toBeOnTheScreen();
});
```

Run: `cd apps/mobile && npm test`
Expected: PASS. Then `npm run typecheck` → no errors.

- [ ] **Step 7: Commit**

```bash
git add apps/mobile
git commit -m "scaffold expo mobile app"
```

---

### Task 3: Styling & animation runtime (NativeWind + Reanimated + gestures)

**Files:**
- Create: `apps/mobile/tailwind.config.js`, `apps/mobile/global.css`, `apps/mobile/nativewind-env.d.ts`
- Modify: `apps/mobile/babel.config.js`, `apps/mobile/metro.config.js`, `apps/mobile/app/_layout.tsx`
- Test: `apps/mobile/__tests__/styling.test.tsx`

**Interfaces:**
- Produces: NativeWind `className` support; `GestureHandlerRootView` + Reanimated available app-wide.

- [ ] **Step 1: Install**

```bash
cd apps/mobile
npx expo install nativewind tailwindcss react-native-reanimated react-native-gesture-handler
```

- [ ] **Step 2: Configure NativeWind + Reanimated**

`babel.config.js`:
```js
module.exports = function (api) {
  api.cache(true);
  return {
    presets: [['babel-preset-expo', { jsxImportSource: 'nativewind' }], 'nativewind/babel'],
    plugins: ['react-native-reanimated/plugin'],
  };
};
```

`metro.config.js`:
```js
const { getDefaultConfig } = require('expo/metro-config');
const { withNativeWind } = require('nativewind/metro');
const config = getDefaultConfig(__dirname);
module.exports = withNativeWind(config, { input: './global.css' });
```

`tailwind.config.js`:
```js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./app/**/*.{ts,tsx}', './src/**/*.{ts,tsx}'],
  presets: [require('nativewind/preset')],
  theme: { extend: {} },
  plugins: [],
};
```

`global.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

`nativewind-env.d.ts`:
```ts
/// <reference types="nativewind/types" />
```

- [ ] **Step 3: Wire providers into the root layout**

`apps/mobile/app/_layout.tsx`:
```tsx
import '../global.css';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { Stack } from 'expo-router';

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <Stack screenOptions={{ headerShown: false }} />
    </GestureHandlerRootView>
  );
}
```

- [ ] **Step 4: Write the failing test**

`apps/mobile/__tests__/styling.test.tsx`:
```tsx
import { render, screen } from '@testing-library/react-native';
import { Text, View } from 'react-native';

test('nativewind className renders without crashing', () => {
  render(<View className="p-4"><Text className="text-lg">hi</Text></View>);
  expect(screen.getByText('hi')).toBeOnTheScreen();
});
```

- [ ] **Step 5: Run tests + typecheck**

Run: `npm test && npm run typecheck`
Expected: PASS (jest-expo transforms nativewind via `transformIgnorePatterns`).

- [ ] **Step 6: Commit**

```bash
git add apps/mobile
git commit -m "add nativewind and reanimated runtime"
```

---

### Task 4: Design tokens & role theming

**Files:**
- Create: `apps/mobile/src/theme/tokens.ts`
- Create: `apps/mobile/src/theme/roles.ts`
- Test: `apps/mobile/src/theme/__tests__/tokens.test.ts`

**Interfaces:**
- Produces: `colors`, `radii`, `spacing`, `type` constants; `type Role = 'patient' | 'doctor' | 'pharmacy'`; `roleTheme(role): { primary: string; primaryFg: string; accentBg: string }`; `acuityColor(a: Acuity): string`.

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/theme/__tests__/tokens.test.ts`:
```ts
import { colors, acuityColor, roleTheme } from '@/theme/tokens';
import { roleTheme as _r } from '@/theme/roles';

test('acuity scale is the medical colour-blind-safe scale', () => {
  expect(acuityColor('ROUTINE')).toBe('#15803D');
  expect(acuityColor('PRIORITY')).toBe('#CA8A04');
  expect(acuityColor('URGENT')).toBe('#EA580C');
  expect(acuityColor('EMERGENCY')).toBe('#B91C1C');
});

test('patient theme is green, doctor/pharmacy navy', () => {
  expect(roleTheme('patient').primary).toBe('#2E8B57');
  expect(roleTheme('doctor').primary).toBe('#003366');
  expect(roleTheme('pharmacy').primary).toBe('#003366');
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm test -- tokens`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement tokens**

`apps/mobile/src/theme/tokens.ts`:
```ts
import type { Acuity } from '@nadi/shared-types';

export const colors = {
  // brand (spec §4 chosen palette)
  seaGreen: '#2E8B57', brightGreen: '#4BB543', lightGrey: '#F4F4F4',
  navy: '#003366', lightBlue: '#A2C2E1',
  surface: '#FFFFFF', border: '#E4E6E1', text: '#14201C', textMuted: '#5E6B66',
  // acuity (ProjectPlan §12 — kept)
  routine: '#15803D', priority: '#CA8A04', urgent: '#EA580C', emergency: '#B91C1C',
} as const;

export const radii = { sm: 8, md: 14, lg: 20, pill: 999 } as const;
export const spacing = { xs: 4, sm: 8, md: 16, lg: 24, xl: 32, xxl: 48 } as const;
export const type = { h1: 30, h2: 24, h3: 20, body: 17, sm: 15, xs: 13 } as const;

const ACUITY: Record<Acuity, string> = {
  ROUTINE: colors.routine, PRIORITY: colors.priority,
  URGENT: colors.urgent, EMERGENCY: colors.emergency,
};
export const acuityColor = (a: Acuity): string => ACUITY[a];

export type Role = 'patient' | 'doctor' | 'pharmacy';
export function roleTheme(role: Role) {
  if (role === 'patient') {
    return { primary: colors.seaGreen, primaryFg: '#FFFFFF', accentBg: colors.lightGrey };
  }
  return { primary: colors.navy, primaryFg: '#FFFFFF', accentBg: colors.lightBlue };
}
```

`apps/mobile/src/theme/roles.ts` re-exports for convenience:
```ts
export { roleTheme, type Role } from '@/theme/tokens';
```

- [ ] **Step 4: Run to verify it passes**

Run: `npm test -- tokens`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/mobile/src/theme
git commit -m "add design tokens and role theming"
```

---

### Task 5: Contract zod schemas

Mirror `@nadi/shared-types` at runtime so every API response is validated at the boundary (spec §4 "contract safety").

**Files:**
- Create: `apps/mobile/src/api/schemas.ts`
- Test: `apps/mobile/src/api/__tests__/schemas.test.ts`

**Interfaces:**
- Produces: zod schemas + inferred types `TokenPair`, `TriageResult`, `Doctor`, `QueueItem`, `Prescription`, `Offer`, `IntakeResult`, `TriagePending`, and `parse<T>(schema, data)`.

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/api/__tests__/schemas.test.ts`:
```ts
import { DoctorSchema, TriageResultSchema, TokenPairSchema } from '@/api/schemas';

test('DoctorSchema accepts a valid doctor with coordinates', () => {
  const d = DoctorSchema.parse({
    id: 'u1', name: 'Dr A', specialty: 'Cardiology', qualifications: 'MBBS',
    experienceYears: 5, distanceKm: 2.1, lat: 19.99, lng: 73.79, feeInr: 400,
    rating: 4.6, reviewCount: 12, languages: ['Hindi'], nextSlot: '09:00',
    photoUrl: 'x', availableSlots: ['09:00'],
  });
  expect(d.lat).toBeCloseTo(19.99);
});

test('TriageResultSchema rejects an unknown acuity', () => {
  expect(() => TriageResultSchema.parse({ acuity: 'MILD' })).toThrow();
});

test('TokenPairSchema requires role', () => {
  expect(() => TokenPairSchema.parse({ accessToken: 'a', refreshToken: 'r', userId: 'u' })).toThrow();
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm test -- schemas`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement schemas**

`apps/mobile/src/api/schemas.ts`:
```ts
import { z } from 'zod';

export const AcuitySchema = z.enum(['ROUTINE', 'PRIORITY', 'URGENT', 'EMERGENCY']);

export const TokenPairSchema = z.object({
  accessToken: z.string(), refreshToken: z.string(),
  role: z.enum(['patient', 'doctor', 'pharmacy']), userId: z.string(),
});

export const LabValueSchema = z.object({
  analyte: z.string(), value: z.number(), unit: z.string(),
  refRange: z.string(), flag: z.enum(['L', 'N', 'H']),
});

export const TriageResultSchema = z.object({
  acuity: AcuitySchema, acuityConfidence: z.number(),
  specialties: z.array(z.object({ name: z.string(), score: z.number() })),
  drivers: z.array(z.object({ feature: z.string(), contribution: z.number() })),
  labs: z.array(LabValueSchema), redFlags: z.array(z.string()), modelVersion: z.string(),
});
export const TriagePendingSchema = z.object({ status: z.literal('pending') });
export const TriageResponseSchema = z.union([TriagePendingSchema, TriageResultSchema]);

export const DoctorSchema = z.object({
  id: z.string(), name: z.string(), specialty: z.string(), qualifications: z.string(),
  experienceYears: z.number(), distanceKm: z.number(), lat: z.number(), lng: z.number(),
  feeInr: z.number(), rating: z.number(), reviewCount: z.number(),
  languages: z.array(z.string()), nextSlot: z.string(),
  photoUrl: z.string(), availableSlots: z.array(z.string()),
});

export const QueueItemSchema = z.object({
  id: z.string(), patientName: z.string(), patientAge: z.number(),
  patientSex: z.enum(['M', 'F', 'O']), acuity: AcuitySchema, complaint: z.string(),
  bookedFor: z.string(), triage: TriageResultSchema,
});

export const PrescriptionLineSchema = z.object({
  drug: z.string(), strength: z.string(), frequency: z.string(),
  durationDays: z.number(), notes: z.string().nullish(), // backend sends null, not omitted
});
export const PrescriptionSchema = z.object({
  id: z.string(), patientName: z.string(), doctorName: z.string(), issuedAt: z.string(),
  lines: z.array(PrescriptionLineSchema),
  status: z.enum(['PENDING', 'ACCEPTED', 'DECLINED', 'DELIVERED']),
});
export const OfferSchema = z.object({
  id: z.string(), prescriptionId: z.string(), patientName: z.string(),
  status: z.enum(['PENDING', 'ACCEPTED', 'DECLINED']), lines: z.array(PrescriptionLineSchema),
});

export const ConsultationDetailSchema = z.object({
  id: z.string(),
  status: z.enum(['PENDING', 'TRIAGED', 'BOOKED', 'IN_PROGRESS', 'DONE']),
  doctorId: z.string().nullish(),
  bookedFor: z.string().nullish(),
  prescriptionId: z.string().nullish(),
});

export const PharmacySchema = z.object({
  id: z.string(), name: z.string(), distanceKm: z.number(),
  deliversInMins: z.number(), isOpen: z.boolean(),
});
export const IntakeResultSchema = z.object({ consultationId: z.string(), jobId: z.string() });

export type TokenPair = z.infer<typeof TokenPairSchema>;
export type TriageResult = z.infer<typeof TriageResultSchema>;
export type Doctor = z.infer<typeof DoctorSchema>;
export type QueueItem = z.infer<typeof QueueItemSchema>;
export type Prescription = z.infer<typeof PrescriptionSchema>;
export type Offer = z.infer<typeof OfferSchema>;
export type IntakeResult = z.infer<typeof IntakeResultSchema>;
export type ConsultationDetail = z.infer<typeof ConsultationDetailSchema>;
export type Pharmacy = z.infer<typeof PharmacySchema>;
```
Install zod: `npx expo install zod`.

Note: confirm `OfferSchema` fields against `apps/api/app/schemas/pharmacy.py` (`OfferOut`) during Plan 04 and adjust if the real shape differs; zod parse will fail loudly if so.

- [ ] **Step 4: Run to verify it passes**

Run: `npm test -- schemas`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/mobile/src/api/schemas.ts apps/mobile/src/api/__tests__ apps/mobile/package.json
git commit -m "add zod contract schemas"
```

---

### Task 6: Session store (zustand + SecureStore)

**Files:**
- Create: `apps/mobile/src/store/session.ts`
- Test: `apps/mobile/src/store/__tests__/session.test.ts`

**Interfaces:**
- Consumes: `TokenPair`, `Role`.
- Produces: `useSession()` zustand store with `{ accessToken, refreshToken, role, userId, signIn(pair), setAccessToken(t), signOut() }`; refresh token persisted to `expo-secure-store` on `signIn`, cleared on `signOut`; `restoreSession()` loads a persisted refresh token on launch.

- [ ] **Step 1: Install + mock SecureStore**

```bash
npx expo install expo-secure-store
```
Append to `apps/mobile/jest.setup.ts`:
```ts
jest.mock('expo-secure-store', () => {
  const store: Record<string, string> = {};
  return {
    setItemAsync: jest.fn(async (k: string, v: string) => { store[k] = v; }),
    getItemAsync: jest.fn(async (k: string) => store[k] ?? null),
    deleteItemAsync: jest.fn(async (k: string) => { delete store[k]; }),
  };
});
```

- [ ] **Step 2: Write the failing test**

`apps/mobile/src/store/__tests__/session.test.ts`:
```ts
import * as SecureStore from 'expo-secure-store';
import { useSession } from '@/store/session';

const pair = { accessToken: 'a', refreshToken: 'r', role: 'doctor' as const, userId: 'u1' };

beforeEach(() => useSession.getState().signOut());

test('signIn stores tokens and persists refresh token', async () => {
  await useSession.getState().signIn(pair);
  expect(useSession.getState().accessToken).toBe('a');
  expect(useSession.getState().role).toBe('doctor');
  expect(SecureStore.setItemAsync).toHaveBeenCalledWith('nadi.refresh', 'r');
});

test('signOut clears state and secure storage', async () => {
  await useSession.getState().signIn(pair);
  await useSession.getState().signOut();
  expect(useSession.getState().accessToken).toBeNull();
  expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('nadi.refresh');
});
```

- [ ] **Step 3: Run to verify it fails**

Run: `npm test -- session`
Expected: FAIL — module not found.

- [ ] **Step 4: Implement the store**

```bash
npx expo install zustand
```
`apps/mobile/src/store/session.ts`:
```ts
import * as SecureStore from 'expo-secure-store';
import { create } from 'zustand';
import type { Role } from '@/theme/tokens';
import type { TokenPair } from '@/api/schemas';

const REFRESH_KEY = 'nadi.refresh';

type SessionState = {
  accessToken: string | null;
  refreshToken: string | null;
  role: Role | null;
  userId: string | null;
  signIn: (pair: TokenPair) => Promise<void>;
  setAccessToken: (token: string) => void;
  signOut: () => Promise<void>;
  restoreSession: () => Promise<void>;
};

export const useSession = create<SessionState>((set) => ({
  accessToken: null, refreshToken: null, role: null, userId: null,
  signIn: async (pair) => {
    await SecureStore.setItemAsync(REFRESH_KEY, pair.refreshToken);
    set({ accessToken: pair.accessToken, refreshToken: pair.refreshToken,
          role: pair.role, userId: pair.userId });
  },
  setAccessToken: (token) => set({ accessToken: token }),
  signOut: async () => {
    await SecureStore.deleteItemAsync(REFRESH_KEY);
    set({ accessToken: null, refreshToken: null, role: null, userId: null });
  },
  restoreSession: async () => {
    const token = await SecureStore.getItemAsync(REFRESH_KEY);
    if (token) set({ refreshToken: token });
  },
}));
```
Note: `restoreSession` recovers only the refresh token; the app exchanges it for an access token + role via `/v1/auth/refresh` on launch (wired in Task 9). Role is re-derived server-side, never trusted from storage.

- [ ] **Step 5: Run to verify it passes**

Run: `npm test -- session`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/mobile/src/store apps/mobile/jest.setup.ts apps/mobile/package.json
git commit -m "add session store with secure refresh-token persistence"
```

---

### Task 7: API client with refresh-once interceptor

**Files:**
- Create: `apps/mobile/src/api/client.ts`
- Test: `apps/mobile/src/api/__tests__/client.test.ts`

**Interfaces:**
- Consumes: `useSession`, `TokenPairSchema`, `parse`.
- Produces: `api.get(path, schema)`, `api.post(path, body, schema?)`, `apiPutBytes(url, bytes, contentType)`; on a `401` the client calls `/v1/auth/refresh` **once**, updates the access token, and retries; a second `401` (or refresh failure) calls `signOut()` and throws `ApiError`.

- [ ] **Step 1: Write the failing test (with msw)**

`apps/mobile/src/api/__tests__/client.test.ts`:
```ts
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { z } from 'zod';
import { api, ApiError } from '@/api/client';
import { useSession } from '@/store/session';

const BASE = 'http://test.local';
process.env.EXPO_PUBLIC_API_URL = BASE;
const server = setupServer();
beforeAll(() => server.listen());
afterEach(() => { server.resetHandlers(); useSession.setState({ accessToken: null, refreshToken: 'r0' }); });
afterAll(() => server.close());

test('get parses a valid response', async () => {
  server.use(http.get(`${BASE}/v1/ping`, () => HttpResponse.json({ ok: true })));
  const out = await api.get('/v1/ping', z.object({ ok: z.boolean() }));
  expect(out.ok).toBe(true);
});

test('refreshes once on 401 then retries', async () => {
  let calls = 0;
  server.use(
    http.get(`${BASE}/v1/secure`, () => {
      calls += 1;
      return calls === 1 ? new HttpResponse(null, { status: 401 }) : HttpResponse.json({ ok: true });
    }),
    http.post(`${BASE}/v1/auth/refresh`, () => HttpResponse.json({ accessToken: 'new' })),
  );
  const out = await api.get('/v1/secure', z.object({ ok: z.boolean() }));
  expect(out.ok).toBe(true);
  expect(useSession.getState().accessToken).toBe('new');
});

test('signs out when refresh fails', async () => {
  server.use(
    http.get(`${BASE}/v1/secure`, () => new HttpResponse(null, { status: 401 })),
    http.post(`${BASE}/v1/auth/refresh`, () => new HttpResponse(null, { status: 401 })),
  );
  await expect(api.get('/v1/secure', z.object({ ok: z.boolean() }))).rejects.toBeInstanceOf(ApiError);
  expect(useSession.getState().accessToken).toBeNull();
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm test -- client`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the client**

`apps/mobile/src/api/client.ts`:
```ts
import { z } from 'zod';
import { useSession } from '@/store/session';

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

const baseUrl = (): string => {
  const url = process.env.EXPO_PUBLIC_API_URL;
  if (!url) throw new ApiError(0, 'EXPO_PUBLIC_API_URL is not set');
  return url;
};

async function refreshAccessToken(): Promise<boolean> {
  const { refreshToken, setAccessToken } = useSession.getState();
  if (!refreshToken) return false;
  const res = await fetch(`${baseUrl()}/v1/auth/refresh`, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ refreshToken }),
  });
  if (!res.ok) return false;
  const data = (await res.json()) as { accessToken?: string };
  if (!data.accessToken) return false;
  setAccessToken(data.accessToken);
  return true;
}

async function request(path: string, init: RequestInit, retry = true): Promise<Response> {
  const { accessToken } = useSession.getState();
  const headers: Record<string, string> = { ...(init.headers as Record<string, string>) };
  if (accessToken) headers.authorization = `Bearer ${accessToken}`;
  const res = await fetch(`${baseUrl()}${path}`, { ...init, headers });
  if (res.status === 401 && retry) {
    const ok = await refreshAccessToken();
    if (ok) return request(path, init, false);
    await useSession.getState().signOut();
    throw new ApiError(401, 'session expired');
  }
  if (!res.ok) throw new ApiError(res.status, `request failed: ${res.status}`);
  return res;
}

export const api = {
  async get<T>(path: string, schema: z.ZodType<T>): Promise<T> {
    const res = await request(path, { method: 'GET' });
    return schema.parse(await res.json());
  },
  async post<T>(path: string, body: unknown, schema?: z.ZodType<T>): Promise<T> {
    const res = await request(path, {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return schema ? schema.parse(data) : (data as T);
  },
};

export async function apiPutBytes(url: string, bytes: Blob, contentType: string): Promise<void> {
  const res = await fetch(url, { method: 'PUT', headers: { 'content-type': contentType }, body: bytes });
  if (!res.ok) throw new ApiError(res.status, 'upload failed');
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `npm test -- client`
Expected: PASS (all three cases).

- [ ] **Step 5: Commit**

```bash
git add apps/mobile/src/api/client.ts apps/mobile/src/api/__tests__/client.test.ts
git commit -m "add api client with refresh-once interceptor"
```

---

### Task 8: Query provider, polling hook & connectivity banner

**Files:**
- Create: `apps/mobile/src/lib/polling.ts`
- Create: `apps/mobile/src/components/ConnectivityBanner.tsx`
- Create: `apps/mobile/src/providers/QueryProvider.tsx`
- Modify: `apps/mobile/app/_layout.tsx`
- Test: `apps/mobile/src/lib/__tests__/polling.test.ts`

**Interfaces:**
- Produces: `QueryProvider` (React Query client + `focusManager`/`AppState` wiring); `pollInterval(active, ms)` helper returning a React Query `refetchInterval` value that pauses when `active` is false; `ConnectivityBanner` showing an offline/backend-unreachable bar via `expo-network`.

- [ ] **Step 1: Install**

```bash
npx expo install @tanstack/react-query expo-network
```

- [ ] **Step 2: Write the failing test**

`apps/mobile/src/lib/__tests__/polling.test.ts`:
```ts
import { pollInterval } from '@/lib/polling';

test('returns the interval when active', () => {
  expect(pollInterval(true, 1500)).toBe(1500);
});
test('returns false (paused) when inactive', () => {
  expect(pollInterval(false, 1500)).toBe(false);
});
```

- [ ] **Step 3: Run to verify it fails**

Run: `npm test -- polling`
Expected: FAIL — module not found.

- [ ] **Step 4: Implement the helper, provider, and banner**

`apps/mobile/src/lib/polling.ts`:
```ts
export function pollInterval(active: boolean, ms: number): number | false {
  return active ? ms : false;
}
```

`apps/mobile/src/providers/QueryProvider.tsx`:
```tsx
import { QueryClient, QueryClientProvider, focusManager } from '@tanstack/react-query';
import { useEffect } from 'react';
import { AppState, type AppStateStatus } from 'react-native';

const client = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 5000 } },
});

export function QueryProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const sub = AppState.addEventListener('change', (status: AppStateStatus) => {
      focusManager.setFocused(status === 'active');
    });
    return () => sub.remove();
  }, []);
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
```

`apps/mobile/src/components/ConnectivityBanner.tsx`:
```tsx
import { useEffect, useState } from 'react';
import { Text, View } from 'react-native';
import * as Network from 'expo-network';

export function ConnectivityBanner() {
  const [online, setOnline] = useState(true);
  useEffect(() => {
    let active = true;
    const check = async () => {
      const state = await Network.getNetworkStateAsync();
      if (active) setOnline(Boolean(state.isInternetReachable ?? state.isConnected));
    };
    check();
    const id = setInterval(check, 5000);
    return () => { active = false; clearInterval(id); };
  }, []);
  if (online) return null;
  return (
    <View className="bg-red-700 px-4 py-2">
      <Text className="text-white text-center" style={{ fontSize: 15 }}>No connection — check Wi-Fi</Text>
    </View>
  );
}
```

Wire both into `apps/mobile/app/_layout.tsx`:
```tsx
import '../global.css';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { Stack } from 'expo-router';
import { QueryProvider } from '@/providers/QueryProvider';
import { ConnectivityBanner } from '@/components/ConnectivityBanner';

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <QueryProvider>
        <ConnectivityBanner />
        <Stack screenOptions={{ headerShown: false }} />
      </QueryProvider>
    </GestureHandlerRootView>
  );
}
```

- [ ] **Step 5: Run tests + typecheck**

Run: `npm test -- polling && npm run typecheck`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/mobile/src/lib apps/mobile/src/providers apps/mobile/src/components/ConnectivityBanner.tsx apps/mobile/app/_layout.tsx apps/mobile/package.json
git commit -m "add query provider, polling helper, connectivity banner"
```

---

### Task 9: UI primitives

**Files:**
- Create: `apps/mobile/src/components/ui/Button.tsx`, `Card.tsx`, `AcuityBadge.tsx`, `Input.tsx`, `Avatar.tsx`, `Skeleton.tsx`, `EmptyState.tsx`, `ErrorState.tsx`
- Create: `apps/mobile/src/components/ui/index.ts`
- Test: `apps/mobile/src/components/ui/__tests__/AcuityBadge.test.tsx`, `Button.test.tsx`

**Interfaces:**
- Consumes: `colors`, `acuityColor`, `type` from theme; `Acuity`.
- Produces: `Button({ title, onPress, variant?, disabled?, loading? })`; `AcuityBadge({ acuity })` rendering colour **and** text label; `Card`, `Input`, `Avatar` (expo-image), `Skeleton`, `EmptyState({ title, message })`, `ErrorState({ message, onRetry })`.

- [ ] **Step 1: Write the failing tests**

`apps/mobile/src/components/ui/__tests__/AcuityBadge.test.tsx`:
```tsx
import { render, screen } from '@testing-library/react-native';
import { AcuityBadge } from '@/components/ui/AcuityBadge';

test('shows the acuity text label, not colour alone', () => {
  render(<AcuityBadge acuity="EMERGENCY" />);
  expect(screen.getByText('Emergency')).toBeOnTheScreen();
});
```

`apps/mobile/src/components/ui/__tests__/Button.test.tsx`:
```tsx
import { fireEvent, render, screen } from '@testing-library/react-native';
import { Button } from '@/components/ui/Button';

test('calls onPress; disabled when loading', () => {
  const onPress = jest.fn();
  const { rerender } = render(<Button title="Book" onPress={onPress} />);
  fireEvent.press(screen.getByText('Book'));
  expect(onPress).toHaveBeenCalledTimes(1);
  rerender(<Button title="Book" onPress={onPress} loading />);
  fireEvent.press(screen.getByTestId('button'));
  expect(onPress).toHaveBeenCalledTimes(1);
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `npm test -- ui`
Expected: FAIL — modules not found.

- [ ] **Step 3: Install expo-image and implement primitives**

```bash
npx expo install expo-image
```

`AcuityBadge.tsx`:
```tsx
import { Text, View } from 'react-native';
import type { Acuity } from '@nadi/shared-types';
import { acuityColor, type as t } from '@/theme/tokens';

const LABEL: Record<Acuity, string> = {
  ROUTINE: 'Routine', PRIORITY: 'Priority', URGENT: 'Urgent', EMERGENCY: 'Emergency',
};
export function AcuityBadge({ acuity }: { acuity: Acuity }) {
  return (
    <View style={{ backgroundColor: acuityColor(acuity), borderRadius: 999,
      paddingHorizontal: 12, paddingVertical: 4, alignSelf: 'flex-start' }}>
      <Text style={{ color: '#FFFFFF', fontSize: t.xs, fontWeight: '700' }}>{LABEL[acuity]}</Text>
    </View>
  );
}
```

`Button.tsx` (56dp tall, full width, disabled/loading):
```tsx
import { ActivityIndicator, Pressable, Text } from 'react-native';
import { colors, radii, type as t } from '@/theme/tokens';

type Props = { title: string; onPress: () => void; variant?: 'primary' | 'ghost';
  disabled?: boolean; loading?: boolean; color?: string };

export function Button({ title, onPress, variant = 'primary', disabled, loading, color }: Props) {
  const bg = variant === 'primary' ? (color ?? colors.seaGreen) : 'transparent';
  const fg = variant === 'primary' ? '#FFFFFF' : (color ?? colors.seaGreen);
  const off = disabled || loading;
  return (
    <Pressable testID="button" accessibilityRole="button" disabled={off} onPress={onPress}
      style={{ height: 56, borderRadius: radii.md, backgroundColor: bg, opacity: off ? 0.5 : 1,
        alignItems: 'center', justifyContent: 'center', width: '100%' }}>
      {loading ? <ActivityIndicator color={fg} />
        : <Text style={{ color: fg, fontSize: t.body, fontWeight: '600' }}>{title}</Text>}
    </Pressable>
  );
}
```

`Card.tsx`, `Input.tsx`, `Avatar.tsx`, `Skeleton.tsx`, `EmptyState.tsx`, `ErrorState.tsx`:
```tsx
// Card.tsx
import { View } from 'react-native';
import { colors, radii, spacing } from '@/theme/tokens';
export function Card({ children }: { children: React.ReactNode }) {
  return <View style={{ backgroundColor: colors.surface, borderRadius: radii.md,
    borderWidth: 1, borderColor: colors.border, padding: spacing.md }}>{children}</View>;
}
```
```tsx
// Input.tsx
import { TextInput } from 'react-native';
import { colors, radii, spacing, type as t } from '@/theme/tokens';
type Props = { value: string; onChangeText: (v: string) => void; placeholder?: string;
  keyboardType?: 'default' | 'phone-pad' | 'number-pad'; multiline?: boolean };
export function Input(p: Props) {
  return <TextInput value={p.value} onChangeText={p.onChangeText} placeholder={p.placeholder}
    keyboardType={p.keyboardType} multiline={p.multiline} placeholderTextColor={colors.textMuted}
    style={{ minHeight: 48, borderWidth: 1, borderColor: colors.border, borderRadius: radii.sm,
      paddingHorizontal: spacing.md, fontSize: t.body, color: colors.text }} />;
}
```
```tsx
// Avatar.tsx
import { Image } from 'expo-image';
export function Avatar({ uri, size = 56 }: { uri: string; size?: number }) {
  return <Image source={{ uri }} style={{ width: size, height: size, borderRadius: size / 2 }}
    contentFit="cover" transition={150} cachePolicy="disk" />;
}
```
```tsx
// Skeleton.tsx
import { useEffect } from 'react';
import Animated, { useAnimatedStyle, useSharedValue, withRepeat, withTiming } from 'react-native-reanimated';
import { colors, radii } from '@/theme/tokens';
export function Skeleton({ height = 16, width = '100%' as number | `${number}%` }) {
  const o = useSharedValue(0.4);
  useEffect(() => { o.value = withRepeat(withTiming(1, { duration: 800 }), -1, true); }, [o]);
  const style = useAnimatedStyle(() => ({ opacity: o.value }));
  return <Animated.View style={[{ height, width, backgroundColor: colors.border, borderRadius: radii.sm }, style]} />;
}
```
```tsx
// EmptyState.tsx
import { Text, View } from 'react-native';
import { colors, spacing, type as t } from '@/theme/tokens';
export function EmptyState({ title, message }: { title: string; message: string }) {
  return <View style={{ alignItems: 'center', padding: spacing.xl, gap: spacing.sm }}>
    <Text style={{ fontSize: t.h3, color: colors.text, fontWeight: '600' }}>{title}</Text>
    <Text style={{ fontSize: t.sm, color: colors.textMuted, textAlign: 'center' }}>{message}</Text>
  </View>;
}
```
```tsx
// ErrorState.tsx
import { Text, View } from 'react-native';
import { Button } from '@/components/ui/Button';
import { colors, spacing, type as t } from '@/theme/tokens';
export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return <View style={{ alignItems: 'center', padding: spacing.xl, gap: spacing.md }}>
    <Text style={{ fontSize: t.body, color: colors.emergency, textAlign: 'center' }}>{message}</Text>
    <Button title="Try again" onPress={onRetry} variant="ghost" />
  </View>;
}
```
`apps/mobile/src/components/ui/index.ts`:
```ts
export { Button } from '@/components/ui/Button';
export { Card } from '@/components/ui/Card';
export { AcuityBadge } from '@/components/ui/AcuityBadge';
export { Input } from '@/components/ui/Input';
export { Avatar } from '@/components/ui/Avatar';
export { Skeleton } from '@/components/ui/Skeleton';
export { EmptyState } from '@/components/ui/EmptyState';
export { ErrorState } from '@/components/ui/ErrorState';
```

- [ ] **Step 4: Run tests + typecheck**

Run: `npm test -- ui && npm run typecheck`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/mobile/src/components/ui apps/mobile/package.json
git commit -m "add ui primitives"
```

---

### Task 10: Auth flow & role-based routing

**Files:**
- Create: `apps/mobile/src/api/auth.ts`
- Create: `apps/mobile/app/(auth)/phone.tsx`, `apps/mobile/app/(auth)/otp.tsx`
- Create: `apps/mobile/app/(patient)/_layout.tsx`, `apps/mobile/app/(doctor)/_layout.tsx`, `apps/mobile/app/(pharmacy)/_layout.tsx`
- Create: `apps/mobile/src/providers/ThemeProvider.tsx`
- Modify: `apps/mobile/app/index.tsx` (launch gate)
- Test: `apps/mobile/src/api/__tests__/auth.test.ts`

**Interfaces:**
- Consumes: `api`, `TokenPairSchema`, `useSession`, `roleTheme`.
- Produces: `requestOtp(phone)`, `verifyOtp({ phone, code, name?, role? })` returning a parsed `TokenPair`; three route groups `(patient)`, `(doctor)`, `(pharmacy)`, each a themed empty portal shell; `index.tsx` routes to the correct group by `role` (or to `(auth)/phone` when signed out).

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/api/__tests__/auth.test.ts`:
```ts
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { requestOtp, verifyOtp } from '@/api/auth';

const BASE = 'http://test.local';
process.env.EXPO_PUBLIC_API_URL = BASE;
const server = setupServer();
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

test('verifyOtp returns a parsed token pair with role', async () => {
  server.use(
    http.post(`${BASE}/v1/auth/request-otp`, () => HttpResponse.json({ sent: true })),
    http.post(`${BASE}/v1/auth/verify-otp`, () =>
      HttpResponse.json({ accessToken: 'a', refreshToken: 'r', role: 'pharmacy', userId: 'u9' })),
  );
  await requestOtp('+915000020001');
  const pair = await verifyOtp({ phone: '+915000020001', code: '123456' });
  expect(pair.role).toBe('pharmacy');
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm test -- auth`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the auth API**

`apps/mobile/src/api/auth.ts`:
```ts
import { api } from '@/api/client';
import { TokenPairSchema, type TokenPair } from '@/api/schemas';
import { z } from 'zod';

export async function requestOtp(phone: string): Promise<void> {
  await api.post('/v1/auth/request-otp', { phone }, z.object({ sent: z.boolean() }));
}

export async function verifyOtp(input: {
  phone: string; code: string; name?: string; role?: string;
}): Promise<TokenPair> {
  return api.post('/v1/auth/verify-otp', {
    phone: input.phone, code: input.code, name: input.name ?? '', role: input.role ?? 'patient',
  }, TokenPairSchema);
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `npm test -- auth`
Expected: PASS.

- [ ] **Step 5: Build the auth screens**

`apps/mobile/app/(auth)/phone.tsx`:
```tsx
import { useState } from 'react';
import { Text, View } from 'react-native';
import { router } from 'expo-router';
import { Button, Input } from '@/components/ui';
import { requestOtp } from '@/api/auth';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function PhoneScreen() {
  const [phone, setPhone] = useState('+91');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submit = async () => {
    setLoading(true); setError(null);
    try { await requestOtp(phone); router.push({ pathname: '/(auth)/otp', params: { phone } }); }
    catch { setError('Could not send the code. Check your connection.'); }
    finally { setLoading(false); }
  };
  return (
    <View style={{ flex: 1, padding: spacing.lg, gap: spacing.md, justifyContent: 'center' }}>
      <Text style={{ fontSize: t.h1, color: colors.text, fontWeight: '700' }}>Welcome to NADI</Text>
      <Text style={{ fontSize: t.sm, color: colors.textMuted }}>Enter your phone number to continue</Text>
      <Input value={phone} onChangeText={setPhone} keyboardType="phone-pad" placeholder="+91…" />
      {error ? <Text style={{ color: colors.emergency, fontSize: t.sm }}>{error}</Text> : null}
      <Button title="Send code" onPress={submit} loading={loading} />
    </View>
  );
}
```

`apps/mobile/app/(auth)/otp.tsx`:
```tsx
import { useState } from 'react';
import { Text, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Button, Input } from '@/components/ui';
import { verifyOtp } from '@/api/auth';
import { useSession } from '@/store/session';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function OtpScreen() {
  const { phone } = useLocalSearchParams<{ phone: string }>();
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const signIn = useSession((s) => s.signIn);
  const submit = async () => {
    setLoading(true); setError(null);
    try {
      const pair = await verifyOtp({ phone: phone!, code, name });
      await signIn(pair);
      router.replace('/');
    } catch { setError('Invalid code. Use 123456 for the demo.'); }
    finally { setLoading(false); }
  };
  return (
    <View style={{ flex: 1, padding: spacing.lg, gap: spacing.md, justifyContent: 'center' }}>
      <Text style={{ fontSize: t.h2, color: colors.text, fontWeight: '700' }}>Enter the code</Text>
      <Text style={{ fontSize: t.sm, color: colors.textMuted }}>Sent to {phone}</Text>
      <Input value={code} onChangeText={setCode} keyboardType="number-pad" placeholder="123456" />
      <Input value={name} onChangeText={setName} placeholder="Your name (new patients)" />
      {error ? <Text style={{ color: colors.emergency, fontSize: t.sm }}>{error}</Text> : null}
      <Button title="Verify" onPress={submit} loading={loading} />
    </View>
  );
}
```

- [ ] **Step 6: Build the theme provider and role shells**

`apps/mobile/src/providers/ThemeProvider.tsx`:
```tsx
import { createContext, useContext } from 'react';
import { roleTheme, type Role } from '@/theme/tokens';

const ThemeCtx = createContext(roleTheme('patient'));
export const useTheme = () => useContext(ThemeCtx);
export function ThemeProvider({ role, children }: { role: Role; children: React.ReactNode }) {
  return <ThemeCtx.Provider value={roleTheme(role)}>{children}</ThemeCtx.Provider>;
}
```

Each role layout wraps its stack in the themed provider. `apps/mobile/app/(patient)/_layout.tsx`:
```tsx
import { Stack } from 'expo-router';
import { ThemeProvider } from '@/providers/ThemeProvider';
export default function PatientLayout() {
  return <ThemeProvider role="patient"><Stack screenOptions={{ headerShown: false }} /></ThemeProvider>;
}
```
`(doctor)/_layout.tsx` and `(pharmacy)/_layout.tsx` are identical with `role="doctor"` / `role="pharmacy"`. Add a placeholder `index.tsx` in each group:
```tsx
import { Text, View } from 'react-native';
import { useTheme } from '@/providers/ThemeProvider';
export default function Home() {
  const theme = useTheme();
  return <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
    <Text style={{ color: theme.primary, fontSize: 24, fontWeight: '700' }}>Portal</Text>
  </View>;
}
```

- [ ] **Step 7: Launch gate routes by role**

`apps/mobile/app/index.tsx`:
```tsx
import { useEffect, useState } from 'react';
import { ActivityIndicator, View } from 'react-native';
import { Redirect } from 'expo-router';
import { useSession } from '@/store/session';

export default function Index() {
  const role = useSession((s) => s.role);
  const restore = useSession((s) => s.restoreSession);
  const [ready, setReady] = useState(false);
  useEffect(() => { restore().finally(() => setReady(true)); }, [restore]);
  if (!ready) return <View style={{ flex: 1, justifyContent: 'center' }}><ActivityIndicator /></View>;
  if (role === 'patient') return <Redirect href="/(patient)" />;
  if (role === 'doctor') return <Redirect href="/(doctor)" />;
  if (role === 'pharmacy') return <Redirect href="/(pharmacy)" />;
  return <Redirect href="/(auth)/phone" />;
}
```
Note: full launch-time refresh-token exchange (restore → `/v1/auth/refresh` → set role) is finalised in Plan 02; here `restoreSession` only recovers the token and the gate falls through to login when role is null.

- [ ] **Step 8: Verify on a device**

Run: `cd apps/mobile && npx expo start`. On a phone with Expo Go (same Wi-Fi, `.env` pointing at the laptop LAN IP, backend up via docker compose): launch → phone screen → enter a new `+91` number → code `123456` + a name → lands on the green patient portal. Repeat with seeded doctor `+915000000001` → navy doctor portal; seeded pharmacy `+9150000200xx` → navy pharmacy portal.

- [ ] **Step 9: Run full gate + commit**

Run: `npm test && npm run typecheck`
Expected: all PASS.
```bash
git add apps/mobile
git commit -m "add otp auth flow and role-based routing"
```

---

## Verification (end of Plan 01)

- `cd apps/mobile && npm test` — all green.
- `cd apps/mobile && npm run typecheck` — no errors.
- `cd apps/api && .venv/Scripts/python -m pytest` — still green (Task 1 change).
- Manual: all three seeded roles log in and land on correctly-themed empty portals on a real device.

**Next plan:** `02-patient-flow` — intake + real report upload, triage polling, doctor list + MapLibre map, booking, jit.si consultation, prescription + pharmacy consent, and the launch-time refresh-token exchange.

# NADI — Production Build (Phase 1.5) Design Spec

> Supersedes the mock-only Phase 1 in `ProjectPlan.md` §13. The frozen API contract (§9),
> data model (§8), and non-negotiables (§14) of `ProjectPlan.md` still govern. This spec
> defines *what we build first, for real*, to reach a live three-device demo.

Date: 2026-10-02

---

## 1. Why this spec exists (scope decision)

`ProjectPlan.md` §13 sequenced a mock-only front-end prototype (Phase 1) before any backend
(Phase 2). We are instead building **production-grade from the start** — a real backend that
all three portals talk to over the internet — because the near-term goal is a **live demo on
three physical Android phones** (patient, doctor, pharmacy) showing the workflow move between
devices in real time. A per-device mock layer cannot do that; a real backend can.

This does **not** change the frozen contract, the data model, or any non-negotiable. It only
changes *when* the real backend arrives (now, not after Phase 1).

### What is real vs. stubbed in this phase

| Real now | Stubbed now (becomes real in a later phase) |
|---|---|
| FastAPI backend, full §9 contract | Trained models M1/M2/M3 → deterministic keyword/rule logic behind the real `/ml/v1/*` routes |
| Postgres 16 + PostGIS, real geo doctor search | Real SMS OTP → fixed test code, but real JWT/session issuance around it |
| Real HTTP from all 3 portals → genuine multi-device sync | Self-hosted Jitsi → public `meet.jit.si` |
| JWT auth, RBAC per role | Celery/async OCR queue → deferred until M2 is a real model (stub responds synchronously) |
| Prescription / consent / pharmacy-routing state machine | — |
| Audit logging, `model_version` on every triage result | — |

**Why ML is stubbed:** trained models require the annotated code-mixed dataset and months of
training (`ProjectPlan.md` Phases 3–4, due end-2026). The stub serves the exact §9 contract so
the swap to real models later touches nothing but the ML service internals. The stub is
steerable by keyword so the demo is reproducible (see §7).

**Why OTP is stubbed:** live SMS to Indian numbers is subject to the TRAI DLT framework, which
filters/delays raw SMS-API senders — an unacceptable risk during a live demo. Real path later =
Firebase Phone Auth (free tier, handles Indian delivery + compliance), an isolated swap.

---

## 2. Architecture

```
3 Android phones (one APK, different role login) ──HTTPS/JSON──┐
                                                               ▼
                               API SERVER (FastAPI, Python 3.11)
                               auth · consultations · doctor search (PostGIS)
                               prescriptions · pharmacy routing · consent · audit
                                     │                         │ internal HTTP
                 ┌───────────────────┘                         ▼
                 ▼                            ML SERVICE (FastAPI, separate deployable)
     Postgres 16 + PostGIS                    /ml/v1/symptom · /document · /triage · /health
     Cloudflare R2 (report images)            deterministic keyword/rule logic (stub)
     Redis (deferred until async OCR real)    → swapped for ONNX models in Phase 4
```

The ML service stays a **separate deployable** even while stubbed, so the real-model swap never
touches the API server (per `ProjectPlan.md` §3).

### Free-tier infrastructure mapping

| Concern | Service | Cost |
|---|---|---|
| Mobile build / distribution | Expo EAS Build → sideloaded APK (no Play Store) | Free |
| API + ML hosting | Render / Railway / Fly.io free tier | Free |
| Database (Postgres + PostGIS) | Supabase free tier (PostGIS as an enabled extension) | Free |
| Cache / broker (when needed) | Upstash Redis free tier | Free |
| Report-image storage | Cloudflare R2 (pre-signed URLs only) | Free |
| Video | Public `meet.jit.si` | Free |
| ML training (later) | Colab / Kaggle free GPU | Free |

Only unavoidable future cost: one-time **$25 Google Play fee**, and only if we ever publish to
the store. Not needed for the demo.

---

## 3. Repository structure

Follows `ProjectPlan.md` §5 (monorepo), building the subset this phase needs:

```
apps/
  mobile/          # Expo RN — patient app (+ dev role switcher to reach doctor/pharmacy)
  doctor-portal/   # RN Web  (can start inside mobile behind role switcher; extract later)
  pharmacy-portal/ # RN Web  (same)
  api/             # FastAPI — routers / models / schemas / services / migrations / core
  ml-service/      # FastAPI — symptom / document / triage (stub) / runtime / schemas
packages/
  shared-types/    # TS types from the §9 contract
docs/
  superpowers/specs/   # this spec
  decisions/           # ADRs (write one per significant choice)
infra/
  docker-compose.yml   # local Postgres+PostGIS, Redis, MinIO, api, ml-service
```

**Decision to confirm during planning:** whether doctor/pharmacy ship as one Expo app with a
role switcher (fastest for the 3-phone demo — one APK, pick role at login) or as separate RN Web
builds. Leaning one app + role switcher for the demo; extract portals later. (ADR candidate.)

---

## 4. Design system

### Brand palette (replaces `ProjectPlan.md` §12 brand tokens)

```ts
export const brand = {
  seaGreen:   '#2E8B57',  // patient primary
  brightGreen:'#4BB543',  // patient accent / success
  lightGrey:  '#F4F4F4',  // app surface / background
  navy:       '#003366',  // doctor & pharmacy primary; headings
  lightBlue:  '#A2C2E1',  // doctor & pharmacy accent / secondary
};
```

**Role theming:** patient app leads with greens (warm, approachable); doctor & pharmacy portals
lead with navy + light blue (clinical, professional). Makes the three portals instantly
distinguishable on the three demo phones.

### Acuity scale — KEPT from `ProjectPlan.md` §12 (do not replace with brand greens)

```ts
export const acuity = {
  routine:   '#15803D',  // green
  priority:  '#CA8A04',  // yellow
  urgent:    '#EA580C',  // orange
  emergency: '#B91C1C',  // red
};
```

The two brand greens are too close in hue to encode distinct status; this green→yellow→orange→red
scale is medically conventional and colour-blind-distinguishable. **Acuity is always a coloured
badge *with a text label* — never colour alone** (§12 / §14).

### Other tokens (carried from §12)

Radii 8/14/20/999 · spacing 4/8/16/24/32/48 · type scale 30/24/20/17/15/13, body never below 15 ·
min tap target 48×48 dp, primary buttons 56 dp full-width · baseline viewport 360×640 dp ·
every list has a designed empty state; every async view a skeleton, not a spinner · transitions
200–300 ms ease-out. No inline styles / no hard-coded hex in components (tokens only).

---

## 5. Screens by role

All screens are fed by the frozen §9 endpoints. UX patterns adapted from Practo (patient shell)
and DocIndia (symptom→specialty→listing→slot-picker).

### Patient app (green theme)
| Screen | Source endpoint(s) | Notes |
|---|---|---|
| Onboarding / language | — | hi / mr / en; Practo-style |
| Phone login + OTP | `POST /v1/auth/request-otp`, `/verify-otp` | OTP stubbed (fixed code), real tokens |
| Home | — | location + symptom search field + mic button (OS recogniser later; canned for now) |
| Reports upload | `POST /v1/uploads/sign` | image-picker grid, skippable; on-device compress later |
| Analyzing | `POST /v1/consultations/intake` → poll `GET .../triage` | 3 fading status lines |
| **Result** | `GET /v1/consultations/{id}/triage` | acuity badge + plain line, top specialty + 2 alts, **"Why we think this" (SHAP drivers)**, lab table. **If `redFlags` non-empty → full-red emergency screen with call button, nothing else.** |
| Doctors listing | `GET /v1/doctors?specialty=&lat=&lng=&radiusKm=&lang=` | DocIndia Fiverr-style: filter rail + sort + verified cards (photo, qualifications, specialty tags, distance, fee, rating, CTA) |
| Doctor detail | `GET /v1/doctors/{id}` | hero + stat tiles + About + sticky slot-picker (date chips → time-grouped slots) |
| Booked | `POST /v1/consultations/{id}/book` | confirmation |
| Consultation | — | Jitsi; network-degradation banner |
| Prescription + consent | `GET /v1/prescriptions/{id}`, `POST .../consent` | **mandatory, unticked, patient-chosen pharmacy multi-select** |

### Doctor portal (navy theme)
| Screen | Source endpoint(s) | Notes |
|---|---|---|
| Queue | `GET /v1/doctor/queue` | sorted by acuity, coloured left border on urgent rows |
| Patient file | `GET /v1/doctor/consultations/{id}` | **NADI Note card** at top (acuity, confidence %, specialty, drivers) — styled distinctly; lab table; actions: start / refer / prescribe |
| Prescription form | `POST /v1/doctor/consultations/{id}/prescribe` | add/remove medicine rows |
| Refer | `POST /v1/doctor/consultations/{id}/refer` | logged as training data |

### Pharmacy portal (navy theme)
| Screen | Source endpoint(s) | Notes |
|---|---|---|
| Inbox | `GET /v1/pharmacy/inbox` | pending first |
| Order detail | `POST /v1/pharmacy/offers/{id}/accept|decline` | per-medicine stock checkboxes; decline → "Forwarded to the next pharmacy" |

---

## 6. Data & API

- **API contract:** exactly `ProjectPlan.md` §9. Frozen. Any change requires an ADR.
- **Data model:** exactly `ProjectPlan.md` §8. PostGIS `geography(Point,4326)`; GiST on all
  `location` columns; btree on `consultations(doctor_id, status, booked_for)`.
- **Invariants (§8/§14):** prescriptions immutable (supersede, never edit); `triage_results.
  model_version` mandatory on every row (stub writes e.g. `stub-keyword-v0`); `audit_log`
  append-only, every patient-record access logged.

---

## 7. Stubbed ML behaviour (steerable demo)

`/ml/v1/triage` returns real §9 `TriageResult` shapes chosen by keyword in the symptom text,
mirroring `ProjectPlan.md` §13:

- `chest` + `breath` → EMERGENCY + red flag (drives the full-red bypass screen)
- `chakkar` / `dizzy` / `weak` → PRIORITY, General Medicine, anaemia lab fixture
- `fever` / `cough` / `cold` → ROUTINE, General Physician
- else → ROUTINE, generic drivers

**Red-flag rules run first and bypass the model entirely** (§6.4 / §14), biased to false
positives: chest pain + breathlessness, one-sided weakness / slurred speech, seizure, severe
bleeding, unresponsiveness, bleeding in pregnancy, high fever in an infant.

`/ml/v1/symptom` returns normalised entities; `/ml/v1/document` returns a `LabValue[]` fixture
(anaemia / thyroid / diabetes panels) — synchronous now, async via Celery once M2 is real.
`drivers` carry plausible SHAP-style contributions so the "Why we think this" card and the NADI
Note look real.

---

## 8. Seed data

Real rows in Postgres (not client fixtures), so the live demo has authentic-looking data:
- **10 doctors** — authentic Indian names, real specialties, locations near Nashik, Maharashtra
  (real lat/lng for PostGIS), 2–40 km spread, ₹200–800 fees, 3.8–4.9 ratings, languages from
  {Hindi, Marathi, English}, sourced royalty-free headshots.
- **6 queue items** spanning all four acuity levels.
- **5 pharmacies** — Maharashtra names, some closed.
- **Lab fixtures** — anaemia, thyroid, diabetes panels with real analyte names, units, ref ranges.

---

## 9. Multi-device demo flow

One EAS-built APK on all three phones; each logs in as a different role against the same live
backend. Walk: patient submits symptoms on Phone A → appears in doctor's queue on Phone B (same
server record) → doctor reviews NADI Note, consults, prescribes → patient consents to pharmacies
→ prescription lands in pharmacy inbox on Phone C → pharmacy accepts → patient notified. No
relay hacks, no pre-seeded fixture trickery — genuine shared server state.

(Live push via FCM is a later polish; for the demo, React Query refetch-on-focus / short polling
is acceptable and far simpler.)

---

## 10. Assets

| Asset | Owner | Authenticity |
|---|---|---|
| Doctor headshots (~10) | **Claude** sources royalty-free, good-looking | must look authentic |
| Fake/anonymised lab reports (anaemia/thyroid/diabetes) | **User** provides | must look authentic |
| NADI logo / wordmark | **User** provides | must look authentic |
| Speciality icons, pharmacy logos, empty states, patient avatars | Claude (lucide / generated) | placeholder-fine |

---

## 11. Non-negotiables (from `ProjectPlan.md` §14 — re-read before any change)

1. NADI **routes, does not diagnose** — no copy/model/field implies a diagnosis.
2. Red-flag rules **bypass the model**, biased to false positives.
3. Never report plain accuracy for triage — **under-triage rate** is the headline safety metric.
4. **`model_version` on every triage result** (stub included).
5. **Pharmacy consent: mandatory, unticked, patient-chosen.** Legal (Telemedicine Guidelines 2020).
6. **No commission on medicine sales.**
7. **Prescriptions immutable** — supersede, never edit.
8. **API contract frozen** — changes require an ADR.
9. **All inference server-side.**
10. **No LLMs/VLMs/third-party AI APIs** — every model is one we train and can evaluate.
11. **No AI attribution** in any committed artefact.

---

## 12. Out of scope this phase

Trained M1/M2/M3 · real SMS OTP · self-hosted Jitsi · Celery async OCR queue · on-device image
compression / edge-blur detection · real OS speech recognition · certificate pinning · DB-at-rest
encryption hardening · load/field testing. Each is a later `ProjectPlan.md` phase and swaps in
behind the frozen contract without touching screens.

---

## 13. Build order

1. `infra/docker-compose.yml` — Postgres+PostGIS, Redis, MinIO, api, ml-service up locally.
2. `apps/api` skeleton — FastAPI, SQLAlchemy models + Alembic migrations for §8, config/security/deps.
3. Auth — stubbed OTP issuing real JWT access+refresh; RBAC dependency per role.
4. `packages/shared-types` — TS types from the §9 contract.
5. `apps/ml-service` — stub `/ml/v1/*` with keyword logic (§7) + red-flag rules.
6. Core API routers (thin; logic in `services/`): consultations+intake, doctors (PostGIS search),
   prescriptions, pharmacies, consent, audit.
7. Seed script — §8 data (10 doctors, 6 queue items, 5 pharmacies, lab panels).
8. `apps/mobile` — scaffold, NativeWind, tokens (§4), UI primitives, typed `api/client.ts` → live backend.
9. Patient flow end to end (incl. red-flag bypass + Result SHAP card).
10. Doctor flow end to end (NADI Note card).
11. Pharmacy flow end to end.
12. Polish — transitions, skeletons, empty states; Hindi labels on patient screens.
13. Deploy api + ml-service to free tier; EAS build APK; sideload on 3 phones; rehearse.

**Rule:** do not start a step before the previous one runs. Write an ADR in `docs/decisions/`
for each significant choice (hosting provider, one-app-vs-separate-portals, polling-vs-push).

---

## 14. Open items to resolve in planning

- One Expo app + role switcher vs. three separate builds (§3) — ADR.
- Hosting provider: Render vs. Railway vs. Fly.io — ADR.
- Demo sync: React Query polling (simple) vs. FCM push (closer to production) — can defer push.

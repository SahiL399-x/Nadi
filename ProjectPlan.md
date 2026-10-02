# NADI — Project Context and Implementation Plan

> Single source of truth for this repository. Read fully before writing code.
> **Current phase is Phase 1 (prototype). See section 13 for what to build right now.**

---

## 1. What NADI is

A telemedicine platform for rural India connecting three groups: **patients**, **doctors**, and **pharmacies**.

A patient describes their symptoms in plain language and optionally photographs their lab reports. Server-side models read the reports, decide how urgent the case is and which medical specialty it belongs to, and match the patient to suitable nearby doctors. The doctor receives the patient file with a machine-generated triage note before the consultation, then consults by video, refers onward, or issues a digital prescription. With the patient's explicit consent, that prescription is routed to nearby pharmacies until one confirms stock and delivers.

**NADI does not diagnose.** It decides *where a patient should go and how urgently*. This is a clinical and legal boundary, not a wording preference. No UI copy, model output, or variable name may state or imply a diagnosis.

### Project type and constraints

Final-year B.E. major project (Mumbai University), built by a small team, due end of 2026. These constraints are fixed:

- **No LLM-based solutions.** No OpenAI/Anthropic/Gemini API calls, no local LLMs, no vision-language models for document extraction. Every model must be one we train or fine-tune ourselves and can evaluate reproducibly.
- **Not an automation/workflow project.** No n8n, Zapier, or pipeline-orchestration framing.
- **No hardware.** Software only.
- **Android only.** Do not write iOS-specific code or spend effort on iOS layout.
- **Not offline-first.** The network is assumed usually available but slow and unstable. We optimise for low bandwidth, not zero connectivity.
- **Video consultations must work**, degrading gracefully on weak networks.

### The academic contribution

Three trained models (section 6), plus an original annotated dataset of code-mixed Indian-language symptom text. The three-portal app is the delivery vehicle that demonstrates them.

---

## 2. Users and roles

| Role | Device | Primary need |
|---|---|---|
| Patient | Budget Android phone, 3–4 GB RAM, weak 4G | Describe a problem without needing to read well or know medical terms |
| Doctor | Laptop browser or phone | Decide quickly whether a case is theirs, and act |
| Pharmacy | Counter PC or phone | See a prescription, confirm stock, deliver |

The patient is the constraining user. Design decisions default to their needs: large tap targets, high contrast, icons with every label, short plain sentences, Hindi and Marathi support.

---

## 3. System architecture

Four deployable units.

```
┌──────────────────────────────────────────────────────────┐
│  MOBILE APP (React Native / Expo)        Android         │
│  Patient flow. Thin client — no ML runs here.            │
│  On-device work is limited to: image compression,        │
│  document edge detection, blur check, audio capture.     │
└───────────────────────┬──────────────────────────────────┘
                        │ HTTPS / JSON
┌───────────────────────┴──────────────────────────────────┐
│  WEB PORTALS (React Native Web, same components)         │
│  Doctor portal · Pharmacy portal                         │
└───────────────────────┬──────────────────────────────────┘
                        │
┌───────────────────────┴──────────────────────────────────┐
│  API SERVER (FastAPI)                                    │
│  Auth · bookings · doctor search (PostGIS) ·             │
│  prescriptions · pharmacy routing · consent · audit      │
│  Postgres 16 + PostGIS · Redis · Celery · R2 storage     │
└───────────────────────┬──────────────────────────────────┘
                        │ internal HTTP
┌───────────────────────┴──────────────────────────────────┐
│  ML SERVICE (separate FastAPI deployable)                │
│  M1 symptom text · M2 report extraction · M3 triage      │
│  ONNX Runtime, INT8 quantised, CPU inference             │
└──────────────────────────────────────────────────────────┘
```

**The ML service is deliberately separate** from the API server. It lets us redeploy a model without redeploying the app, and give the models more resources than the booking logic needs.

### Why all models run server-side

1. **Accuracy.** Shrinking fine-tuned models to fit a low-end phone would lose the accuracy we spent months earning.
2. **App size.** Budget Android devices ship with 32 GB storage, most of it consumed. Bundled models would make the app several hundred MB.
3. **Traceability — the decisive reason.** This is clinical decision support. We must be able to say exactly which model version produced which recommendation. On-device inference means every user runs whatever version they last downloaded, destroying the audit trail and removing our ability to disable a misbehaving model.

---

## 4. End-to-end flow

```
PATIENT
  1. Opens app, picks language (hi / mr / en)
  2. Types symptoms into a search field.
     A mic button uses the OS speech recogniser to fill the field.
     This is NOT our model — it is android.speech.SpeechRecognizer.
  3. Optionally photographs lab reports.
     On-device: detect page edges, check sharpness, crop, downscale to
     1600px, encode WebP q75. ~4 MB raw becomes ~200 KB.
  4. POST /v1/consultations/intake

SERVER
  5. Report images → Celery job → ML service M2 → structured lab values
  6. Symptom text → ML service M1 → normalised symptom entities
  7. Both + demographics → ML service M3 → acuity, top-3 specialties,
     SHAP drivers
  8. Red-flag rules run FIRST and bypass the model entirely (section 6.4)
  9. PostGIS query: doctors of matching specialty within radius,
     ranked by distance, availability, rating

PATIENT
 10. Sees matched doctors, books a slot

DOCTOR
 11. Queue sorted by acuity. Opens patient file.
 12. Reads the NADI Note: acuity + confidence + specialty + drivers
 13. Video consultation (Jitsi), degrading to audio on weak networks
 14. Then one of:
       a. Issues a structured prescription
       b. Re-refers to another specialty  ← LOGGED AS TRAINING DATA
       c. Advises a physical visit

PATIENT
 15. Consent screen: selects which pharmacies may receive the prescription.
     Mandatory. Not skippable. Nothing pre-ticked. (See section 11.)

PHARMACY
 16. Receives prescription, confirms stock or declines
 17. On decline, routed to the next consented pharmacy
 18. Patient notified by push and SMS
```

**Step 14b is the feedback loop.** Every re-referral is a labelled example of a routing mistake. This is the one part of the system that improves over time and our main differentiator from existing platforms.

---

## 5. Repository structure

Monorepo.

```
apps/
  mobile/                      # React Native (Expo) — patient app
    app/                       # expo-router routes
    src/
      api/                     # client + types + mock layer
      components/ui/           # design system primitives
      store/                   # zustand
      theme/tokens.ts
      i18n/
      lib/
  doctor-portal/               # React Native Web
  pharmacy-portal/             # React Native Web

  api/                         # FastAPI
    routers/                   # auth, consultations, doctors,
                               #   prescriptions, pharmacies, admin
    models/                    # SQLAlchemy ORM
    schemas/                   # pydantic request/response
    services/                  # business logic (keep routers thin)
    workers/                   # celery tasks
    migrations/                # alembic
    core/                      # config, security, deps

  ml-service/                  # FastAPI, separate deployable
    symptom/                   # M1
    document/                  # M2
    triage/                    # M3
    runtime/                   # ONNX session management
    schemas/                   # MUST match apps/api/schemas

packages/
  shared-types/                # TS types generated from OpenAPI
  ui-kit/                      # components shared across portals

ml/                            # research, not production
  datasets/
    symptom-text/              # our original annotated corpus
    report-images/
    triage-labels/
  notebooks/                   # EDA and error analysis only
  training/                    # reproducible scripts, not notebooks
  evaluation/                  # fixed test sets + metric scripts
  export/                      # ONNX conversion + quantisation

docs/
  api-contract.md              # FROZEN
  annotation-guidelines.md
  decisions/                   # ADR-0001.md, ADR-0002.md, ...
  architecture/                # DFD, ER, sequence diagrams

infra/
  docker-compose.yml
  .github/workflows/
```

**Write an ADR** in `docs/decisions/` for every significant technical choice: context, options considered, decision, what we gave up. Short files. These get used directly in the project viva.

---

## 6. The machine learning

### M1 — Symptom text understanding

**Input:** free-text symptom description, code-mixed and mixed-script.
**Output:** normalised symptom entities + a clean canonical string.

Rural users type romanised Hinglish (`"mujhe chakkar aa raha hai"`, `"pet me jalan"`, `"sar bhari lag raha"`), while OS voice typing in Hindi produces Devanagari. The model must handle both scripts, colloquial symptom vocabulary, and heavy misspelling.

**Approach:** MuRIL encoder (pretrained on Indian languages *including transliterated Latin script* — this is why it beats plain BERT here) fine-tuned for symptom entity extraction and normalisation.
**Dataset:** ours. Collected and annotated by the team. Augmented via transliteration and spelling perturbation.
**Baseline to beat:** keyword/regex matching against a symptom lexicon.

### M2 — Report understanding

**Input:** photograph of a lab report.
**Output:** `[{analyte, value, unit, refRange, flag}]`.

**Pipeline:** docTR (OCR) → LayoutLMv3 (field association) → BioBERT/scispaCy NER (fine-tuned) → unit normalisation and reference-range comparison.

**Use docTR, not PaddleOCR.** On a published clinical-report benchmark PaddleOCR ranked lowest on numeric accuracy (0.674 vs docTR 0.884) and was ~17× slower on CPU (14.1 s/img vs 0.81 s/img). Numeric accuracy is exactly what matters — a misread haemoglobin value is worse than no value.

**Evaluation:** field-level recall over the five attributes (name, value, unit, reference range, abnormality), following the MedRepBench protocol. Using a published protocol rather than one we invented is a credibility win.

### M3 — Triage and routing

**Input:** normalised symptoms + structured labs + age/sex.
**Output:** `acuity`, `acuityConfidence`, top-3 `specialties` with scores, `drivers` (SHAP contributions).

**Approach:** XGBoost on engineered features as the baseline; MuRIL text encoder fused with a gradient-boosted tabular head as the final model.

**Class imbalance is the central modelling problem.** Most cases are routine. Never report plain accuracy — a model that always predicts ROUTINE would score ~85%. Report macro-F1, per-class recall, and above all the **under-triage rate**.

**Train with asymmetric cost.** Over-triage wastes a consultation slot. Under-triage harms a person. Optimise recall on high-acuity classes and accept the precision loss. Use focal loss or class weights.

**Explainability is mandatory.** SHAP drivers are surfaced in the doctor's UI. A model that outputs "HIGH PRIORITY" with no reason is useless to a physician and will not pass review.

### 6.4 Red-flag rules — not a model

Hard-coded deterministic rules that run **before** M3 and bypass it entirely:

- chest pain with breathlessness
- one-sided weakness or slurred speech
- seizure
- severe bleeding
- unresponsiveness
- bleeding during pregnancy
- high fever in an infant

When any fires, the app immediately shows a full-screen emergency instruction to go to the nearest facility, with a call button. No model output is shown. These rules are deliberately biased toward false positives.

### Targets

| Model | Metric | Target | Baseline |
|---|---|---|---|
| M1 | Entity-level F1 | > 0.85 | Regex lexicon match |
| M2 | Field recall (5 attrs) | > 0.85 | Rule-based extractor |
| M3 | Specialty top-3 accuracy | > 0.90 | TF-IDF + LogReg |
| M3 | Recall on high-acuity | > 0.95 | XGBoost |
| M3 | **Under-triage rate** | **< 3%** | — |
| System | Bytes per consultation | < 500 KB (excl. video) | ~5 MB unoptimised |
| System | p95 triage latency | < 4 s | — |

**Top-3 accuracy is the honest metric for specialty routing**, because the patient is shown three doctors, not one.

---

## 7. Tech stack

### Mobile (`apps/mobile`)

| Purpose | Package | Notes |
|---|---|---|
| Framework | Expo SDK latest, React Native, TypeScript strict | New Architecture on |
| Navigation | `expo-router` | File-based |
| Styling | `nativewind` | Tailwind syntax |
| Client state | `zustand` | |
| Server state | `@tanstack/react-query` | Cache-first, background refetch, retries |
| Animation | `react-native-reanimated` | |
| Icons | `lucide-react-native` | |
| Camera | `react-native-vision-camera` | Frame processors for edge/blur detection |
| Images | `expo-image`, `expo-image-picker` | |
| Speech input | `expo-speech-recognition` | **Not** `@react-native-voice/voice` — archived Jan 2026, fails silently on New Architecture |
| Local cache | `expo-sqlite` + `react-native-mmkv` | Cache only, not a sync engine |
| Push | FCM via `notifee` | |
| Video | Jitsi Meet React Native SDK | |
| i18n | `i18next` | hi, mr, en |
| Errors | Sentry | |

**Speech input caveat:** Android on-device recognition requires Android 13+ and a downloaded language pack. Below that it is online-only and throws `ERROR_NETWORK`. `isRecognitionAvailable()` can return true even when it will fail. Always degrade silently to plain typing.

### Backend (`apps/api`)

| Purpose | Choice | Why |
|---|---|---|
| API | FastAPI, Python 3.11 | Same language as ML — no serving bridge |
| DB | PostgreSQL 16 + **PostGIS** | Real geo queries with GiST indexes |
| ORM / migrations | SQLAlchemy 2.x + Alembic | |
| Cache / broker | Redis | |
| Async jobs | Celery | OCR and inference must never block a request |
| Storage | Cloudflare R2 (S3-compatible), MinIO locally | Pre-signed expiring URLs only |
| Auth | Phone OTP → JWT access + refresh | Rural users have numbers, not emails |
| SMS | MSG91 | |
| Video | Jitsi Meet, self-hosted | Free, no per-minute billing |

### ML (`apps/ml-service`, `ml/`)

| Purpose | Choice |
|---|---|
| Training | PyTorch, Hugging Face Transformers, PEFT (LoRA) |
| OCR | docTR |
| Layout | LayoutLMv3 |
| Clinical NER | BioBERT / scispaCy, fine-tuned |
| Text encoder | MuRIL |
| Tabular | XGBoost |
| Explainability | SHAP |
| Serving | ONNX Runtime, INT8 quantisation, CPU |
| Tracking | MLflow |

### Infra

Docker Compose, GitHub Actions, EAS Build for the Android app.

---

## 8. Data model

Core tables. PostGIS `geography(Point, 4326)` for all locations.

```
users              id, phone, role, name, lang, created_at
patients           user_id, age, sex, location
doctors            user_id, specialty, qualifications, reg_number,
                   experience_years, fee_inr, languages[], location,
                   rating, review_count, is_verified
pharmacies         user_id, name, licence_number, location,
                   delivers, open_hours

consultations      id, patient_id, doctor_id, status, booked_for,
                   symptom_text_raw, symptom_text_normalised,
                   created_at
reports            id, consultation_id, object_key, ocr_status
lab_values         id, report_id, analyte, value, unit, ref_range, flag

triage_results     id, consultation_id, acuity, acuity_confidence,
                   specialties jsonb, drivers jsonb, red_flags jsonb,
                   model_version, created_at
referrals          id, consultation_id, from_doctor_id,
                   to_specialty, reason, created_at    ← TRAINING DATA

prescriptions      id, consultation_id, issued_at, status
prescription_lines id, prescription_id, drug, strength, frequency,
                   duration_days, notes
pharmacy_consents  id, prescription_id, pharmacy_id, granted_at
pharmacy_offers    id, prescription_id, pharmacy_id, status,
                   responded_at

audit_log          id, actor_user_id, action, entity, entity_id, at
```

**Rules:**
- Prescriptions are **immutable**. Corrections create a new prescription superseding the old one. Never UPDATE a prescription's clinical content.
- `triage_results.model_version` is mandatory on every row. This is the audit trail.
- `audit_log` is append-only. Every access to a patient record is logged.
- Indexes: GiST on all `location` columns; btree on `consultations(doctor_id, status, booked_for)`.

---

## 9. API contract

Frozen. Changes require an ADR.

```
POST   /v1/auth/request-otp          { phone }
POST   /v1/auth/verify-otp           { phone, code } → tokens
POST   /v1/auth/refresh

POST   /v1/consultations/intake      → { consultationId, jobId }
GET    /v1/consultations/{id}/triage → TriageResult | { status: 'pending' }
GET    /v1/consultations/{id}
POST   /v1/consultations/{id}/book   { doctorId, slot }

GET    /v1/doctors?specialty=&lat=&lng=&radiusKm=&lang=
GET    /v1/doctors/{id}

GET    /v1/doctor/queue
GET    /v1/doctor/consultations/{id}
POST   /v1/doctor/consultations/{id}/refer      { toSpecialty, reason }
POST   /v1/doctor/consultations/{id}/prescribe  { lines[] }

GET    /v1/prescriptions/{id}
POST   /v1/prescriptions/{id}/consent  { pharmacyIds[] }

GET    /v1/pharmacy/inbox
POST   /v1/pharmacy/offers/{id}/accept
POST   /v1/pharmacy/offers/{id}/decline

POST   /v1/uploads/sign              → pre-signed PUT url
```

### ML service (internal only, never publicly exposed)

```
POST /ml/v1/symptom     { text, lang }                → entities, normalised
POST /ml/v1/document    { objectKey }                 → LabValue[]
POST /ml/v1/triage      { symptoms, labs, age, sex }  → TriageResult
GET  /ml/v1/health                                    → model versions
```

### Shared types

```ts
export type Acuity = 'ROUTINE' | 'PRIORITY' | 'URGENT' | 'EMERGENCY';

export interface LabValue {
  analyte: string;      // "Haemoglobin"
  value: number;        // 9.1
  unit: string;         // "g/dL"
  refRange: string;     // "12.0 - 15.5"
  flag: 'L' | 'N' | 'H';
}

export interface TriageInput {
  symptomText: string;
  reportImageUris: string[];
  age?: number;
  sex?: 'M' | 'F' | 'O';
  lang: 'en' | 'hi' | 'mr';
}

export interface TriageResult {
  acuity: Acuity;
  acuityConfidence: number;                          // 0..1
  specialties: { name: string; score: number }[];    // length 3, descending
  drivers: { feature: string; contribution: number }[];
  labs: LabValue[];
  redFlags: string[];                                // non-empty ⇒ EMERGENCY
  modelVersion: string;
}

export interface Doctor {
  id: string; name: string; specialty: string;
  qualifications: string; experienceYears: number;
  distanceKm: number; feeInr: number;
  rating: number; reviewCount: number;
  languages: string[]; nextSlot: string;
  photoUrl: string; availableSlots: string[];
}

export interface QueueItem {
  id: string; patientName: string; patientAge: number;
  patientSex: 'M' | 'F' | 'O';
  acuity: Acuity; complaint: string; bookedFor: string;
  triage: TriageResult;
}

export interface PrescriptionLine {
  drug: string; strength: string; frequency: string;
  durationDays: number; notes?: string;
}

export interface Prescription {
  id: string; patientName: string; doctorName: string;
  issuedAt: string; lines: PrescriptionLine[];
  status: 'PENDING' | 'ACCEPTED' | 'DECLINED' | 'DELIVERED';
}

export interface Pharmacy {
  id: string; name: string;
  distanceKm: number; deliversInMins: number; isOpen: boolean;
}
```

---

## 10. Network strategy

We assume a weak but usually-present 4G connection. Design for the 5th percentile, not the median.

### Shrinking payloads

| What | Approach | Result |
|---|---|---|
| Report images | On-device: crop to detected page, downscale to 1600px long edge, WebP q75 | 4 MB → ~200 KB |
| Audio (if ever recorded) | Opus 16 kHz, 16 kbps, silence trimmed | 640 KB → ~16 KB for 20s |
| List responses | Field masking — request only what the screen renders | |
| Compression | Brotli on all responses | |

### Resilience

- **Resumable chunked uploads.** An upload that dies at 80% resumes at 80%. Non-resumable uploads on a flaky network can loop forever and burn a user's data pack.
- **Exponential backoff** on failures, not an immediate error.
- **Cache-first reads** via React Query — screens render from cache, then refresh.
- **Push, never poll.** An FCM data message is a few hundred bytes; polling costs megabytes a day.
- **Connection-aware quality.** NetInfo drives image quality, request deferral, and video mode.

### Video degradation ladder

Never a dead end. Each rung falls through to the next.

```
> 800 kbps     video at 480p
300–800 kbps   reduced resolution and frame rate
< 300 kbps     audio only — tell both sides why
unstable       doctor calls the patient's phone directly (PSTN)
no data        SMS with a callback number
```

Jitsi handles bitrate adaptation. Our job is the decision logic above it and an honest on-screen indicator of the current mode. **Treat SMS as a first-class channel**, not a legacy fallback — it works on 2G and on a basic phone.

---

## 11. Security and compliance

Use standard, well-understood mechanisms. Invent nothing here.

| Area | Implementation |
|---|---|
| Login | Phone OTP, no passwords. Short-lived JWT access + refresh tokens |
| Access control | RBAC. A doctor sees only patients booked with them. A pharmacy sees the prescription only — never medical history |
| Transit | TLS 1.3 everywhere, certificate pinning in the app |
| At rest | DB encryption on. Report images in encrypted object storage, never in the DB |
| File access | Pre-signed URLs expiring in minutes. Never a public URL |
| Video | WebRTC is encrypted by design. Single-use room tokens |
| Consent | Recorded before reports reach a doctor, and again before a prescription reaches any pharmacy |
| Audit | Every patient-record access logged, append-only |
| Shared phones | App PIN; notification previews never contain medical content |

### Legal requirement — do not get this wrong

The **Telemedicine Practice Guidelines, 2020** require the doctor to obtain the patient's **express consent** before a prescription is sent to a pharmacy, and the pharmacy must be of the **patient's own choosing**. This exists to prevent a doctor–pharmacy nexus. The NMC can blacklist non-compliant platforms.

Therefore:
- The pharmacy consent screen is **mandatory and not skippable**
- Nothing is **pre-ticked**
- The patient selects which pharmacies may receive it
- **We take no commission on medicine sales.** Revenue model is a flat pharmacy listing fee plus a transparent consultation platform fee

Designed against the **DPDP Act 2023**: consent, purpose limitation, encryption, retention limits.

---

## 12. Conventions

- TypeScript strict. No `any`, no `@ts-ignore`.
- Python: type hints everywhere, `ruff` + `black`, pydantic at all boundaries.
- Functional React components with hooks. No class components.
- Components under 150 lines — split when longer.
- No business logic in screen/route files. Put it in `services/` (backend) or `src/lib/` and the store (frontend).
- Routers stay thin — validate, call a service, return. Logic lives in `services/`.
- No inline styles. NativeWind classes or `theme/tokens.ts` values only. No hard-coded hex anywhere in components.
- Baseline viewport is **360×640 dp**. Every screen must work there.
- Commit messages: short, imperative, lowercase. `add patient triage result screen`.
- **No AI or tool attribution anywhere** — not in commits, code comments, file headers, or committed files. No "Generated with", no co-author trailers, no emoji.
- Do not create README, summary, or progress-note files unless explicitly asked.

### Design tokens

```ts
export const colors = {
  bg: '#FAFAF7', surface: '#FFFFFF', border: '#E4E6E1',
  text: '#14201C', textMuted: '#5E6B66',
  primary: '#0F766E', primaryFg: '#FFFFFF', accent: '#C2410C',
  routine: '#15803D', priority: '#CA8A04',
  urgent: '#EA580C', emergency: '#B91C1C',
};
export const radii   = { sm: 8, md: 14, lg: 20, pill: 999 };
export const spacing = { xs: 4, sm: 8, md: 16, lg: 24, xl: 32, xxl: 48 };
```

Type scale 30/24/20/17/15/13. Body never below 15. Minimum tap target 48×48 dp; primary buttons 56 dp tall, full width. Acuity is always a coloured badge **with a text label** — never colour alone. Every list has a designed empty state; every async view has a skeleton, not a spinner. Transitions 200–300 ms, ease-out, subtle. No bouncing.

---

## 13. Phases — what to build when

### The governing decision

**The API contract (section 9) is frozen now.** The entire app is built against a **mock layer** returning those exact shapes. When the real backend and models arrive, only the mock implementations are replaced. No component, screen, or store ever knows whether data is real or fake.

This decouples app development from ML progress completely, and is the most important engineering decision in the plan.

---

### ▶ PHASE 1 — Clickable prototype  ← **WE ARE HERE**

**Goal:** a front-end-only demo covering all three roles with mock data.

**Build:**
- One Expo app containing all three roles, with a dev-only role switcher on the entry screen
- Complete `src/api/types.ts` and `src/api/mock.ts` with realistic fixtures — **finish this before any screen**
- All screens navigable, with transitions, loading skeletons, empty states
- A demo path walkable end to end in under three minutes

**Do NOT build in Phase 1:** backend, database, real network calls, ML, authentication, real video, real speech recognition, tests, CI. If something seems to need these, stub it in the mock layer and move on.

**Mock layer rules:**
```ts
const delay = (ms: number) => new Promise(r => setTimeout(r, ms));

export async function runTriage(input: TriageInput): Promise<TriageResult> {
  await delay(1800);   // deliberate — forces real loading states now
  // choose fixture by keyword in input.symptomText
}
```
Use 1500–2000 ms for triage, 400–800 ms for lists.

`runTriage` picks its response by keyword so the demo is steerable:
- `chest` + `breath` → EMERGENCY with a red flag
- `chakkar` / `dizzy` / `weak` → PRIORITY, General Medicine, anaemia lab fixture
- `fever` / `cough` / `cold` → ROUTINE, General Physician
- anything else → ROUTINE, generic drivers

**Fixtures must look real.** 10 doctors with authentic Indian names, real specialties, 2–40 km distances, ₹200–800 fees, 3.8–4.9 ratings, languages from {Hindi, Marathi, English}, `https://i.pravatar.cc/150?img=N` photos. 6 queue items spanning all four acuity levels. 5 pharmacies with Maharashtra names, some closed. Lab fixtures for anaemia, thyroid and diabetes panels with real analyte names, units and reference ranges. Locations near Nashik, Maharashtra.

**Build order — do not start a step before the previous one runs on a device:**
1. Scaffold, dependencies, NativeWind, verify in Expo Go
2. `theme/tokens.ts` + UI primitives (Button, Card, Badge, Input, Avatar, Skeleton)
3. `api/types.ts` + `api/mock.ts` + all fixtures — complete
4. Navigation skeleton: every route reachable, even if empty
5. Patient flow end to end
6. Doctor flow end to end
7. Pharmacy flow end to end
8. Polish: transitions, skeletons, empty states, haptics
9. Hindi labels on patient screens only

**Screens:**

*Patient* — Home (symptom field + mic button; mic shows a 2 s listening animation then fills canned text) · Reports (image picker grid, skippable) · Analyzing (three fading status lines: "Reading your reports" → "Understanding your symptoms" → "Finding the right doctor") · **Result** (acuity badge with plain-language line, recommended specialty + 2 alternatives, "Why we think this" drivers card, lab table; if `redFlags` is non-empty this screen is replaced entirely by a full-red emergency view with a call button and nothing else) · Doctors (filterable cards) · Doctor detail (profile + slot chips + sticky book bar) · Booked (confirmation) · Consultation (mock video UI; show a "Network is weak — switched to audio only" banner after 4 s) · Prescription (+ mandatory pharmacy consent multi-select)

*Doctor* — Queue (sorted by acuity, coloured left border on urgent rows) · Patient file (**NADI Note card** at top: acuity, confidence %, specialty, drivers — style this distinctly, it is what examiners look at; lab table below; three actions: start consultation / refer / prescribe) · Prescription form (add/remove medicine rows)

*Pharmacy* — Inbox (pending first) · Order detail (per-medicine stock checkboxes; confirm or decline; decline shows "Forwarded to the next pharmacy")

**Done when:** a stranger can be handed the phone and complete the full patient → doctor → pharmacy → patient loop in under three minutes with no crash, blank screen, or raw spinner.

---

### PHASE 2 — Backend

FastAPI, Postgres + PostGIS, Alembic migrations, OTP auth and RBAC, object storage with pre-signed URLs, PostGIS doctor search, prescription routing state machine, consent capture, audit logging, Docker Compose. The ML service exists but returns **stubbed** predictions matching the contract. The mobile app swaps mock functions for real `fetch` calls — nothing else changes.

### PHASE 3 — Data and baselines

Collect and annotate the symptom-text corpus. Write `docs/annotation-guidelines.md`. Hand-label a 200-sample gold evaluation set and compute inter-annotator agreement. Build classical baselines: TF-IDF + logistic regression for specialty, XGBoost for acuity. Fix the test sets now and never touch them again.

### PHASE 4 — Models

Train M1, M2, M3. SHAP explainability. Export to ONNX, quantise INT8, benchmark latency on a CPU box. Replace the stub in the ML service. Nothing else should break — that is the payoff of the frozen contract.

### PHASE 5 — Evaluation and delivery

Ablation studies, error analysis, confusion matrices. Doctor face-validity study (2–3 practising physicians rate 25 generated notes for usefulness and safety). Load test. Network-throttled field testing. Report, paper, demo video.

---

## 14. Things that must not drift

Re-read before any significant change.

1. **The system routes, it does not diagnose.** No copy, model, or field name implies a diagnosis.
2. **Red-flag rules bypass the model** and are biased toward false positives.
3. **Never report plain accuracy** for triage. Under-triage rate is the headline safety metric.
4. **`model_version` is recorded on every triage result.** No exceptions.
5. **Pharmacy consent is mandatory, unticked, and patient-chosen.** Legal requirement.
6. **No commission on medicine sales.**
7. **Prescriptions are immutable.** Supersede, never edit.
8. **The API contract is frozen.** Changing it requires an ADR.
9. **All inference is server-side.**
10. **No LLMs, no VLMs, no third-party AI APIs.** Every model is one we train and can evaluate.
11. **No AI attribution in any committed artefact.**

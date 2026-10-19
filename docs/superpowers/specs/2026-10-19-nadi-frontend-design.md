# NADI Frontend Design — Expo / React Native app (3-phone demo)

Date: 2026-10-19
Status: Approved design (pre-plan)
Supersedes: `ProjectPlan.md` §13 **Phase 1** specifics listed under "Relationship to ProjectPlan" below. Builds on the merged backend (Phase 2, commit `9a282bd`) and the production pivot (ADR-0003, `docs/superpowers/specs/2026-10-02-nadi-production-build-design.md`).

## Goal

A single Expo / React Native app covering all three roles (patient, doctor, pharmacy) that runs live on **three physical Android phones** over a shared LAN, talking to the real FastAPI backend + Postgres/PostGIS + MinIO running on the presenter's laptop. The demo proves genuine cross-device sync: a patient on phone A triggers state the doctor sees on phone B and the pharmacy on phone C, in near real time.

## Hard constraints

- **Strictly $0 for the demo.** No paid service, no credit card, no API key that bills. Deployment to paid/free-tier hosting (Render/Railway/Supabase) is explicitly out of scope and deferred to post-demo.
- **Near-perfect, no loopholes.** Robustness (auth refresh, polling discipline, upload integrity, contract validation, every empty/error state designed) is a first-class requirement, not polish.
- **No AI/tool attribution** anywhere — commits, comments, file headers (ProjectPlan §14.11).
- **The system routes, it does not diagnose** (§14.1). No copy implies a diagnosis.

## Relationship to ProjectPlan

- **Keeps** the §13 screen inventory (patient/doctor/pharmacy screens), §12 conventions (TS strict, components <150 lines, no business logic in route files, no inline styles, 360×640 baseline, 48dp tap targets, designed empty states + skeletons not spinners, 200–300ms ease-out transitions), and the §12 **acuity colour scale** (routine `#15803D`, priority `#CA8A04`, urgent `#EA580C`, emergency `#B91C1C`), always badge **+ text label**.
- **Supersedes** §13 Phase 1's mock-only decisions: there is **no dev role switcher**, **no mock layer**, **no mock video**. The app talks to the real backend, logs in via OTP, and does real video + real report upload.
- **Reconciles the palette:** the user-chosen brand palette replaces §12's teal brand tokens (`primary #0F766E` etc.) for identity/role theming, while the §12 acuity scale, radii, spacing, and type scale are kept verbatim.

---

## Section 1 — Architecture, stack & project layout (approved)

**Stack (locked):** Expo / React Native, TypeScript strict. Navigation **expo-router**; styling **NativeWind**; session state **zustand**; server data **React Query** (cache-first, polling for sync). Not a web app — the responsive-web alternative was explicitly rejected.

**UI / performance deps (all free, standard in Expo):** **react-native-reanimated** + **react-native-gesture-handler** (UI-thread animations/gestures), **@shopify/flash-list** (recycling lists), **expo-image** (cached images), **@maplibre/maplibre-react-native** (open-source map, see §4). Rationale in §6.

**Location:** new app at `apps/mobile/` in the monorepo. Contract types imported from `packages/shared-types`.

**Layering (enforces §12 "no business logic in route files"):**
- `app/` — expo-router routes only (thin; render + navigate).
- `src/api/` — typed API client, one `fetch` wrapper, zod response schemas, React Query hooks.
- `src/lib/` — pure logic (polling hook, upload state machine, acuity formatting, role→theme selection).
- `src/store/` — zustand session store.
- `src/theme/` — `tokens.ts` (palette + §12 scales) + NativeWind theme provider.
- `src/components/` — UI primitives (Button, Card, Badge, Input, Avatar, Skeleton, EmptyState, ErrorState) and shared composites (DoctorCard, AcuityBadge, NadiNote).

**Config:** API base URL is a single value, `EXPO_PUBLIC_API_URL`, pointing at the laptop's LAN IP (phone + laptop on the same Wi-Fi). Changing LAN only touches this one value.

**Roles in one app:** after OTP verify, the app routes to the portal for the **backend-returned `role`** — patient / doctor / pharmacy. No client-side role choice, no switcher.

---

## Section 2 — Screen inventory (approved)

Per ProjectPlan §13, built for all three roles together (not patient-first).

**Auth (shared):** Phone-number entry (+91) → OTP entry (stub code `123456`). Patient self-signs-up (new phone → always patient, captures name). Doctor/pharmacy log in with seeded phone numbers (demo doctor `+915000000001`; seeded pharmacies `+9150000200xx`). Role comes from the backend, app routes accordingly.

**Patient (green app):**
- **Home** — symptom text field + mic button (mic = short listening animation then fills text; speech is canned for the demo), language toggle (en/hi/mr).
- **Reports** — image picker grid. **Real upload** (not skippable-as-stub): selected images are uploaded for real; see §4 upload rules.
- **Analyzing** — three fading status lines ("Reading your reports" → "Understanding your symptoms" → "Finding the right doctor") while polling triage.
- **Result** — acuity badge + plain-language line, recommended specialty + 2 alternatives, "Why we think this" drivers card, lab table. If `redFlags` is non-empty, this screen is **replaced entirely** by a full-red emergency view with a call button and nothing else.
- **Doctors** — filterable cards (specialty, distance, fee, rating, languages), distance shown as text; plus a **MapLibre map view** (toggle) with a pin per doctor using their lat/lng, centred on the patient (see §4). Both list and map are driven by the same `GET /v1/doctors` result.
- **Doctor detail** — profile + stat tiles + date/time slot chips + sticky book bar.
- **Booked** — confirmation.
- **Consultation** — **real** jit.si room `meet.jit.si/nadi-{consultationId}` (join button).
- **Prescription** — prescription lines + **mandatory** pharmacy consent multi-select; after consent, poll status (PENDING → ACCEPTED → DELIVERED).

**Doctor (navy portal):**
- **Queue** — sorted by acuity, coloured left border on urgent rows; polls for live updates.
- **Patient file** — **NADI Note card** at top (acuity, confidence %, specialty, drivers — styled distinctly; this is what examiners look at), lab table below. Actions: start consultation (join same jit.si room) / refer / prescribe.
- **Prescription form** — add/remove medicine rows.

**Pharmacy (navy portal):**
- **Inbox** — offers, pending first; polls for live updates.
- **Order detail** — per-medicine view; accept or decline. Decline shows "Forwarded to the next pharmacy".

---

## Section 3 — Data flow & endpoint mapping

Grounded in the merged backend (`apps/api`), not the frozen contract doc. All routes are `/v1/...`.

**Auth** — `/v1/auth`
- `POST /request-otp` `{phone}` → `{sent:true}` (stub, no SMS).
- `POST /verify-otp` `{phone, code:"123456", role?, name?}` → `TokenPair` **+ authoritative `role`**. App routes to that role's portal.
- `POST /refresh` `{refreshToken}` → `{accessToken}`.
- Session: access token in memory, refresh token in `expo-secure-store`.

**Patient**
1. Reports → `POST /v1/uploads/sign` → HTTP `PUT` bytes to MinIO → collect `objectKey`s.
2. `POST /v1/consultations/intake` `{symptomText, reportImageUris:[keys], age?, sex?, lang}` → `{consultationId, jobId}`.
3. Analyzing/Result → **poll** `GET /v1/consultations/{id}/triage` until `{status:"pending"}` flips to `TriageResult`.
4. Doctors → `GET /v1/doctors?specialty=&lat=&lng=&radiusKm=&lang=` → `Doctor[]`; detail → `GET /v1/doctors/{id}`.
5. Book → `POST /v1/consultations/{id}/book` `{doctorId, slot}` → `{booked:true}`.
6. Consultation → join `meet.jit.si/nadi-{consultationId}`.
7. Prescription → `GET /v1/prescriptions/{id}`; consent → `POST /v1/prescriptions/{id}/consent` `{pharmacyIds:[...]}` → `{consented, routedTo}`; poll prescription `status`.

**Doctor** — `/v1/doctor`
- `GET /queue` → `QueueItem[]` (acuity-sorted, embedded `triage`); poll.
- `POST /consultations/{id}/prescribe` `{lines:[...]}` → `{prescriptionId}`.
- `POST /consultations/{id}/refer` `{toSpecialty, reason}` → `{referred}`.

**Pharmacy** — `/v1/pharmacy`
- `GET /inbox` → offers; poll.
- `POST /offers/{id}/accept` → `{accepted}`.
- `POST /offers/{id}/decline` → `{declined, forwarded}` (backend auto-forwards to next pharmacy).

**Sync strategy:** React Query polling — the backend has no websockets. Patient triage ~1.5s while pending (stops on result); doctor queue + pharmacy inbox ~3–5s. Polling pauses when the app is backgrounded and resumes on focus (`AppState`). This is what makes the 3-phone demo visibly update.

**Video room:** no backend room endpoint exists. Room name is derived client-side from the consultation ID both parties already hold: `meet.jit.si/nadi-{consultationId}`. No backend change, no account, free.

---

## Section 4 — Error/edge handling, robustness & theming

**Cost discipline (the $0 guarantee):** everything runs locally — Expo Go / local dev build on the phones, FastAPI + Postgres/PostGIS + MinIO in Docker on the laptop, public meet.jit.si, bundled fonts, `lucide-react-native` icons, royalty-free headshots already in `seed/doctor_headshots.json`, React Query polling (no paid realtime). **The map is MapLibre + OpenStreetMap** (`@maplibre/maplibre-react-native`) — open-source, **no API key and no billing account anywhere**, so the demo stays strictly card-free. Google Maps / Mapbox are explicitly rejected because they require a credit-card-backed billing account even inside their free tier. AI OCR / report summary (Gemini or any model) is **out of scope** for this build (see Out of scope) — the ML/OCR stub is unchanged, keeping this spec card-free and avoiding any key in the app bundle.

**Backend prerequisite for doctor pins:** `DoctorOut` currently exposes `distanceKm` but not coordinates. Real map pins need two additive fields — `lat`, `lng` — added to `apps/api/app/schemas/doctor.py` (populated from the existing `Doctor.location` PostGIS point) and mirrored in `packages/shared-types`. This is backward-compatible (additive) and is the only backend touch in this frontend build; it should be carried as the first task of the implementation plan or a tiny companion backend change.

**Session & auth:**
- React Query 401 interceptor transparently calls `/v1/auth/refresh` **once**; on refresh failure → clear session → OTP screen. No infinite retry loop.
- App launch reads stored session → routes straight to the role portal; no login flash.

**Networking robustness:**
- Single typed API client; base URL = `EXPO_PUBLIC_API_URL` (one value).
- Every mutation has explicit loading / success / error UI with a retry affordance — never a silent failure.
- Polling uses React Query with backoff and `AppState` awareness (pause on background, resume on focus).
- Offline / backend-unreachable banner (`expo-network`) — the whole demo is LAN-dependent, so this must be visible and distinct.

**Upload (fully real — must be bulletproof):**
- `sign` → `PUT` to MinIO with per-file progress; a failed PUT is retryable per image.
- `intake` is **blocked** until every selected image resolves to an `objectKey` (or the user removes it). A half-uploaded report can never reach intake.
- MinIO-unreachable is messaged **distinctly** from a generic network/backend error, so on stage the failing component is obvious.

**Per-screen states:**
- Triage pending → animated "analysing" state; hard timeout ~30s → graceful "taking longer than usual — keep waiting / retry".
- Empty doctor list, empty queue, empty pharmacy inbox → designed empty states (§12), never blank screens or raw spinners.
- Every async view uses a skeleton, not a spinner (§12).

**Video:**
- Join opens `meet.jit.si/nadi-{consultationId}`; if the in-app WebView/permissions fail, fall back to the system browser with the same URL. Camera/mic permission requested just-in-time with rationale.

**Contract safety (the "no loopholes" core):**
- Mirror `packages/shared-types` with **zod schemas**; parse every API response at the client boundary. Contract drift fails loudly at the seam instead of rendering `undefined` downstream.

**Theming (per role, from the chosen palette):**
- Patient app: greens `#2E8B57` / `#4BB543` on light grey `#F4F4F4` — warm/approachable.
- Doctor + pharmacy portals: navy `#003366` + light blue `#A2C2E1` — clinical/professional.
- Acuity badges keep the §12 medical scale (routine→emergency), always badge **+ text label**, never colour alone (colour-blind-safe).
- Theme selected by the backend-returned `role` at login, applied app-wide via a NativeWind theme provider. No hard-coded hex in components — tokens only (§12).

---

## Section 5 — Testing & verification

TDD per the superpowers flow (tests before implementation), scoped to a 1-week demo — invest where bugs bite on stage, skip harnesses costlier to set up than what they catch.

**Unit / logic — Jest + React Native Testing Library:**
- API client: 401→refresh→retry-once; refresh-fails→logout.
- Triage polling hook: pending→result transition, timeout, pause-on-background.
- Upload state machine: per-file retry; intake blocked until all images resolve.
- Acuity badge: correct colour **+ text label** for each of the 4 levels (colour-blind-safe guarantee asserted).
- zustand session store + role→theme selection.

**Contract safety:** zod schemas mirroring `packages/shared-types`, asserted against representative fixtures; parse-at-boundary in the client.

**Screen/integration — MSW (Mock Service Worker):** each screen rendered against mocked endpoints with loading, success, empty, and error states asserted — so empty-queue / empty-inbox / unreachable-backend aren't first discovered live.

**E2E — deliberately NOT Detox** (setup cost exceeds payoff for a one-week demo). Instead, a written **3-phone verification script** (the real acceptance test): patient self-signs-up → intake with a real report upload → sees triage → books the seeded doctor → doctor sees the case in queue live → both join the jit.si room → doctor prescribes → patient consents to a pharmacy → pharmacy sees the offer in inbox live → accepts → patient sees `ACCEPTED`. Each step is a checklist item with its expected on-screen result. Run against the real LAN backend + MinIO before demo day.

**Verification gates (`superpowers:verification-before-completion`):** `tsc --noEmit` (strict) clean, Jest suite green, one full manual pass of the 3-phone script, **and a smoothness pass on an actual low-end Android device** (§6) — no "done" claim without all four.

---

## Section 6 — Performance & responsiveness (60fps on low-end devices)

**Requirement:** the app must feel fluid even on cheap hardware — the opposite of the laggy government-app experience, where UI stutters because animations and lists run on the JS thread and drop frames whenever JS is busy. The design makes the UI thread independent of JS work.

**Animations never touch the JS thread**
- **react-native-reanimated v3** + **react-native-gesture-handler** for every animation and gesture — they run on the UI thread, so transitions, the "analysing" fades, press feedback, and sheet gestures hold 60fps even while JS is mid-fetch or re-rendering. This is the single most important choice separating NADI from the laggy-gov-app feel.

**Lists that don't jank**
- **FlashList** (`@shopify/flash-list`) instead of `FlatList` for the three heavy lists — doctors, doctor queue, pharmacy inbox. View recycling keeps memory and scroll jank flat on low-end hardware regardless of length.
- **expo-image** instead of RN `Image` for doctor headshots — disk cache, lower memory, faster decode, no flicker on re-render.

**No wasted renders**
- New Architecture (Fabric) + Hermes — both default in current Expo SDK; faster startup, lower memory, better render path.
- zustand selectors kept narrow; React Query `select` so a screen subscribes only to the slice it needs; memoized list rows. Polling already pauses on background, so idle screens cost nothing.
- Heavy work (pre-upload image processing, large list mounts) deferred past the navigation transition via `InteractionManager`, so navigation always feels instant.

**Map performance**
- MapLibre renders natively on the GPU; the map is lazy-mounted behind the list/map toggle so it never costs anything on the critical scroll path, and pin markers are capped to the current result set.

**Perceived speed**
- Skeletons, never spinners (§12); optimistic UI on mutations (book, accept/decline) so taps feel immediate while the request settles; debounced symptom input.

**Measurable gate (not a vibe):** verification includes a pass on a **real low-end Android device** (not just the emulator) — scroll each list, run the full flow, confirm no dropped-frame stutter against a 60fps / 16ms-per-frame budget. "Feels smooth on the cheapest phone in the demo" is an explicit done-criterion.

---

## Out of scope (deferred post-demo)

- Deployment to any host (Render/Railway/Supabase/EAS store builds).
- Firebase Phone Auth (real SMS) — OTP stays stubbed for the demo.
- Trained ML models (Phases 3–5) — ML service stays stubbed.
- **AI OCR lab-field extraction + report summary** (Gemini or any model) — deferred; the user will bring or build an ML model for this later. The current OCR/labs stub is unchanged.
- Google Maps / Mapbox (billing-account-backed) — rejected in favour of card-free MapLibre/OSM.
- Push notifications, websockets, async OCR via Redis/Upstash.
- Google Play publishing ($25 one-time) — only if ever published.

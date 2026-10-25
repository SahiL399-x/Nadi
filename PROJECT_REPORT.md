# NADI — Project Report

*A symptom-to-specialist routing platform for Indian primary care.*

> **How to use this document:** This is a complete source report. Every section is written so you can lift it directly into a slide deck, viva script, or written submission. Where a claim would be stronger with a citation or a live number, there is a **`[add your data]`** marker — fill those with your own references. Nothing here is invented market data; the context statements are framed as reasoning, not statistics.

---

## 1. Executive summary

**NADI is a telehealth triage platform that reads a patient's symptoms (and uploaded lab reports) and routes them to the *right kind of doctor*, then carries that single case — live and in sync — across three devices: the patient's phone, the doctor's portal, and the pharmacy's portal.**

The core insight: in Indian primary care the hardest step for a patient is not *talking to a doctor* — it is *knowing which doctor to talk to*. People with chest pain book a general physician; people with a thyroid problem see three wrong specialists before the right one. NADI compresses that "specialist discovery" step into one screen and makes the whole downstream journey — consult, prescription, pharmacy fulfilment — a single connected flow.

Crucially, **NADI routes, it does not diagnose.** It never tells a patient what disease they have. It estimates *acuity* (how urgent) and *specialty* (who to see), shows *why*, and escalates red-flag emergencies to a call-an-ambulance screen. This is both a safety stance and a regulatory one.

The project is built **production-grade from day one** (real backend, real cross-device sync, real video and file upload) rather than as a clickable mock — because the thing worth demonstrating *is* the live multi-device coordination, which a mock cannot show.

**Current state:** the backend is complete and tested; the mobile app's foundation is nearly finished and the full screen set is planned in detail. A three-phone live demo is the target deliverable.

---

## 2. The name

**NADI** is named after **Nāḍī Parīkṣā** — the Ayurvedic practice of *pulse diagnosis*: reading the body's signals at the wrist to understand the patient's state. The app does the modern, digital equivalent — it *reads the patient's signals* (their described symptoms and their lab reports) and uses them to *understand where to route the patient*. The name ties a 21st-century routing engine to a recognisably Indian medical tradition, which is a deliberate identity choice, not decoration.

---

## 3. The problem

Three friction points in the patient's path to correct care:

1. **Specialist discovery is guesswork.** A symptom ("breathlessness", "joint pain", "irregular periods") maps to a specialty that a layperson often doesn't know. Wrong first choice → wasted consult, wasted money, delayed care.
2. **The journey is fragmented.** Finding a doctor, consulting, getting a prescription, and getting medicines are four disconnected experiences across four apps/places. State is lost at every handoff.
3. **Urgency is invisible.** Nothing in a normal booking flow tells a patient "this looks like an emergency — don't book a 3-day-out slot, call an ambulance now."

NADI targets all three with one connected flow and an explicit acuity signal.

> `[add your data]` — If your report wants market framing, add a line on India's doctor-to-patient ratio and the share of first consultations that reach the wrong specialty. Cite your own source; this report deliberately does not fabricate figures.

---

## 4. What NADI is — the three-role system

One app, three role-specific experiences, selected automatically by the role the backend returns at login (no client-side role switch).

### 4.1 Patient (green theme — warm, approachable)
- **Home** with two entry paths:
  - **Symptom hero** (NADI's core): type or speak symptoms in English / Hindi / Marathi → triage.
  - **Specialty grid**: browse doctors directly by specialty, skipping triage.
- **Reports**: photograph lab reports; they are really uploaded (not faked).
- **Analyzing → Result**: an acuity badge + plain-language routing ("We suggest seeing a Cardiologist"), the *drivers* behind that suggestion, and any lab values. **Red-flag symptoms replace the whole screen with a full-red "seek care now / call 108" view.**
- **Doctors**: filterable list + a real map of nearby doctors; book a slot.
- **Consultation**: an in-app video room shared with the doctor.
- **Prescription + pharmacy consent**: the patient explicitly chooses which pharmacy/pharmacies may see their prescription (a legal requirement), then watches the order status update live.

### 4.2 Doctor (navy theme — clinical, professional)
- **Dashboard** with real stats (appointments today, pending, completed, prescriptions issued, new patients).
- **Live queue** sorted by acuity (emergencies first, coloured left border).
- **Appointments board** by date with status (Upcoming / Arrived / In Progress / Completed).
- **Patient file** — the **NADI Note** (acuity, confidence, specialty, drivers) plus the patient's medical history (conditions, allergies, family history, past visits and prescriptions) and a **private, per-author notes** area.
- **Prescribe** with medicine-catalog autocomplete; **refer** to another specialty.
- **Availability editor** and **profile**.

### 4.3 Pharmacy (navy theme)
- **Dashboard** (New / In Progress / Out for Delivery / Completed counts).
- **Orders board** filterable by lifecycle state.
- **Order detail** that advances an order through a *validated* lifecycle (Preparing → Out for delivery → Delivered → Completed) — illegal transitions are rejected by the server.
- **New-requests inbox**: accept an incoming prescription, or decline → it auto-forwards to the next pharmacy the patient consented to.

### 4.4 The money shot — cross-device sync
The demo's whole point: a patient action on phone A appears on the doctor's phone B and the pharmacy's phone C within seconds, because all three talk to one real backend. Patient books → doctor's queue updates → doctor prescribes → patient's prescription screen fills → patient consents to a pharmacy → pharmacy's inbox lights up → pharmacy accepts → patient's status flips to accepted. **No mock could show this; that is why the backend is real.**

---

## 5. How it is built — architecture

### 5.1 High-level shape
```
  Patient phone ┐
  Doctor phone  ┼─ HTTP (LAN/Wi-Fi) ─▶  FastAPI backend ─▶ Postgres + PostGIS
  Pharmacy phone┘                         │                 (relational + geo)
                                          ├─▶ MinIO (S3-compatible report storage)
                                          └─▶ ML service (deterministic triage stub)
   Video: self-hosted LiveKit (WebRTC); backend mints a per-consultation join token
   Map:   MapLibre + OpenStreetMap tiles (no key, no billing)
```

### 5.2 Frontend — Expo / React Native
- **Expo + React Native, TypeScript strict.** One codebase, three role portals.
- **expo-router** (file-based navigation), **NativeWind** (Tailwind-style styling), **zustand** (session state), **React Query** (server data + polling).
- **Performance is a first-class requirement** (see §8): animations run on the UI thread (Reanimated), lists recycle (FlashList), images cache (expo-image).
- **Why native, not a web app:** the demo runs on physical Android phones and needs camera/mic for video and the file picker for reports — a decision taken explicitly over a responsive web build.

### 5.3 Backend — FastAPI + Postgres/PostGIS
- **FastAPI** (Python), thin routers with logic in a service layer, pydantic models at every boundary.
- **Postgres + PostGIS** for relational data *and* geospatial queries (nearest doctors / pharmacies by real distance).
- **Alembic migrations** (schema versions 0001→0008) that run automatically on startup, then a comprehensive **demo seed** populates realistic Nashik/Maharashtra data so every screen looks full and real in front of examiners — **real database rows served by real endpoints, never hardcoded responses.**
- **MinIO** (S3-compatible) stores the uploaded report images; the client gets a signed URL and uploads the bytes directly.
- Containerised with Docker Compose — one command brings up the whole stack.

### 5.4 The triage / ML service
- A dedicated service exposes the triage endpoints. **Today it runs deterministic keyword/rule logic** (symptom → specialty, symptom → acuity, red-flag detection) that stands in for trained models.
- The **contract is frozen** so that when real models arrive (Phases 3–5) they drop in behind the same interface with no frontend change. This is a deliberate "stub now, swap later" design — the honest framing is that *the plumbing is real and the model is a placeholder*, not that the AI is trained.

### 5.5 Video and maps — chosen to cost nothing
- **Video:** **self-hosted LiveKit** (open-source WebRTC) running in the same Docker stack. For each consultation the backend mints a short-lived LiveKit join token for a deterministic room (`nadi-<consultationId>`), so patient and doctor meet in the same room without any paid service — no account, no key, free at any scale on your own hardware. (LiveKit Cloud's free tier is the documented fallback if LAN WebRTC media misbehaves.)
- **Maps:** MapLibre with OpenStreetMap tiles — open-source, **no API key and no billing account**. (Google Maps / Mapbox were explicitly rejected because even their free tiers require a card-backed billing account.)

### 5.6 Engineering discipline
- **Test-driven:** backend has a full pytest suite; the mobile app is built test-first (Jest + React Native Testing Library + MSW for mocked endpoints).
- **Contract safety:** every API response is validated at the client boundary with zod schemas mirroring the shared types — contract drift fails loudly at the seam instead of rendering `undefined` three screens later.
- **Built via a reviewed, task-by-task pipeline:** each unit of work is implemented, tested, and independently reviewed for spec-compliance and quality before the next begins, with a durable progress ledger so the build can resume exactly where it left off after any interruption.

---

## 6. Why NADI is different

| Dimension | Typical doctor-booking apps (e.g. Practo-style) / govt telemedicine (eSanjeevani-style) | **NADI** |
|---|---|---|
| **Primary job** | "Book a doctor you already chose" | **"Figure out *which* doctor, then book"** — triage-first |
| **Urgency signal** | Usually absent | **Explicit acuity** (routine→emergency), colour + label, red-flag emergency takeover |
| **The journey** | Booking and pharmacy are separate products | **One connected case** across patient → doctor → pharmacy, live |
| **Lab reports** | Attach-and-forget | Uploaded, surfaced to the doctor as structured context (field extraction is the ML roadmap) |
| **Diagnosis stance** | Varies | **Never diagnoses — routes only**, by design and by copy |
| **Cost to run the demo** | N/A | **₹0 / no billing account anywhere** (open-source map, public video, local infra) |
| **Accessibility of language** | Often English-first | Symptom entry in **English / Hindi / Marathi** |
| **Performance target** | Often janky on cheap phones | **Explicit 60fps-on-low-end-Android requirement**, architected (UI-thread animation, list recycling) not retrofitted |
| **Privacy model** | Coarse | **RBAC** (pharmacy never sees medical history; doctor sees only their own patients) + **per-author private notes** + **explicit pharmacy consent** |

The one-line version for a viva: **"Practo helps you book a doctor. NADI tells you *which* doctor — and then keeps the whole case moving across everyone involved, in real time, for free."**

> `[add your data]` — Name the specific competitors you want to contrast (Practo, 1mg, Tata Health, eSanjeevani) and, if you have screenshots, cite that these were studied as UX references rather than copied.

---

## 7. Safety, ethics & compliance

These are not add-ons; they shaped the design.

- **"Routes, does not diagnose."** No screen, field, or copy implies a diagnosis. The system outputs *who to see* and *how urgent*, with the drivers behind it — never *what disease you have*. This keeps NADI on the right side of medical-device/diagnosis regulation and is the single most important ethical guardrail.
- **Red-flag escalation.** Emergency-indicating symptoms bypass the whole booking funnel and show a call-an-ambulance (108) screen. The system fails *safe*.
- **Acuity is colour-blind-safe.** The urgency scale is always a coloured badge **plus a text label**, never colour alone, using a medically conventional green→yellow→orange→red scale.
- **Pharmacy consent is mandatory and patient-driven.** A prescription is only ever routed to a pharmacy the patient explicitly selected (nothing pre-ticked) — aligned with India's Telemedicine Practice Guidelines (2020) principle that the patient chooses their pharmacy.
- **Role-based access control.** A pharmacy sees the prescription and patient name — never the medical history. A doctor sees only patients booked with them. Enforced server-side, not just hidden in the UI.
- **Consultation notes are private per author.** Each side's notes are their own notebook; the other side never sees them.

> `[add your data]` — If you want a compliance slide, cite the Telemedicine Practice Guidelines 2020 (Board of Governors / MCI) directly.

---

## 8. Performance as a design requirement

A stated goal: **NADI must feel fluid on the cheapest Android phone in the room** — the opposite of the laggy government-app experience, where UI stutters because animation and list work compete with JavaScript on one thread.

Design decisions that make this structural rather than cosmetic:
- **Animations never touch the JS thread** — Reanimated runs them on the UI thread, so transitions stay at 60fps even while a network fetch is mid-flight.
- **Lists recycle** — FlashList keeps memory and scroll-jank flat regardless of list length (doctor lists, queues, order boards).
- **Images cache and decode cheaply** — expo-image for doctor photos.
- **Narrow re-renders** — zustand selectors and React Query `select` so a screen subscribes only to the slice it needs; skeletons instead of spinners; optimistic UI on taps.
- **The map is lazy-mounted** so it never costs anything on the scroll path.

The acceptance test is explicit: a smoothness pass on a *real* low-end device, not just an emulator.

---

## 9. Current status (honest)

| Component | Status |
|---|---|
| **Backend (core)** | ✅ Complete, merged, tested — FastAPI + Postgres/PostGIS + ML stub, auth, triage, doctors, booking, prescriptions, pharmacy consent/forwarding, uploads. |
| **Backend (v2 portals)** | ✅ Complete, merged — doctor dashboard/stats/appointments/patient-history/availability/profile, medicine catalog, pharmacy order lifecycle + stats, big demo seed. Migrations 0001→0008; ~47 tests green; clean rebuild verified. |
| **Shared contract types** | ✅ Mirrored for the frontend. |
| **Mobile foundation** (scaffold, theming, zod contracts, session, API client with auth-refresh, polling/connectivity, UI primitives, OTP auth + role routing) | 🟢 ~90% — final auth/routing task in progress; everything before it built test-first and reviewed. |
| **Mobile patient flow** | 📝 Fully planned (intake, real upload, triage result + emergency view, doctor list + map, booking, in-app video, prescription + consent). |
| **Mobile doctor & pharmacy portals** | 📝 Fully planned (dashboards, appointments, patient file, prescribe-with-search, orders lifecycle board). |
| **In-app video (LiveKit)** | ✅ Implemented — backend token endpoint + in-app LiveKit room component, shared patient/doctor. On-device media render is a demo-day gate (needs the native dev build). |
| **Trained ML models** | ⏳ Roadmap (Phases 3–5). Triage runs on a deterministic stub today. |

**Plain-English version for the report:** *"The entire backend is built and tested. The app's foundations are built and tested. The remaining screens are specified task-by-task and are being implemented now against the already-working backend."*

---

## 10. Challenges we face now — and how we'll fix them

This is the "what's hard and what's next" section; each item is a real risk with a concrete mitigation.

### 10.1 The ML is a stub, not a trained model (the honest centrepiece challenge)
- **Challenge:** triage currently uses deterministic keyword/rule logic, not a trained model. Real symptom→specialty and lab-field extraction need annotated data and training that cannot exist in a one-week build.
- **Fix / roadmap:** Phases 3–5 — a **free, open-source ML stack**: on-device/served OCR (Google ML Kit / PaddleOCR — strong on the tables lab reports actually are), rule+regex field extraction first, then a free biomedical NER model for messier documents, and a **template-based note** generated from extracted entities (no LLM, so it stays "routes, not diagnoses"). The frozen contract means these drop in with zero frontend change. A commercial clinical-NLP option was evaluated and **rejected** because it requires a paid licence and heavy runtime — violating the $0 constraint.

### 10.2 In-app video (WebRTC + Expo) has real integration friction
- **Challenge:** the first choice, the Jitsi React Native SDK, had **no build for our React Native version** and a 28-package native-dependency chain (several git forks) — it broke both the EAS bundle and the Gradle build. We **switched to LiveKit**, whose React Native SDK has no version trap, but WebRTC on React Native still needs a **native dev build** (not plain Expo Go) and real cameras/mics on two devices to exercise end-to-end.
- **Fix:** LiveKit is **self-hosted and open-source**, so it is free at any scale and under our control; **LiveKit Cloud's free tier is kept as a documented fallback** if LAN WebRTC media misbehaves on stage. On-device two-phone render is an explicit demo-day verification gate.

### 10.3 Authentication is stubbed for the demo
- **Challenge:** OTP is a fixed demo code (`123456`), not real SMS. Live SMS in India runs into the TRAI DLT sender-registration framework, a regulatory/time risk for a stage demo.
- **Fix:** real JWT/session issuance is already in place; only the SMS leg is stubbed. Post-demo we swap in **Firebase Phone Auth** (free tier, handles Indian delivery + compliance) behind the same flow.

### 10.4 The demo depends on a local LAN
- **Challenge:** all three phones and the laptop must share one Wi-Fi; a flaky network is a visible failure mode.
- **Fix:** a **distinct, always-visible offline banner** so a network drop is obviously a network drop (not a bug in the app); the API base URL is a single config value, so switching networks is a one-line change; post-demo, deploy the backend to a free tier (Render/Railway + Supabase) to remove the LAN dependency entirely.

### 10.5 No real-time push; we poll
- **Challenge:** the backend has no websockets, so cross-device updates arrive via polling, not instant push.
- **Fix:** tuned polling intervals (fast while a patient is waiting on triage, slower for queues/inboxes) that pause when the app is backgrounded. It is visibly "a few seconds", which is fine for the demo; websockets/push are a post-demo enhancement.

### 10.6 Toolchain version churn (a real build-time cost we hit)
- **Challenge:** the app sits on a very new Expo / React Native / React stack where library versions disagree (e.g. a styling library that only supports the previous major of its CSS engine). These break *at build/runtime*, invisibly to unit tests.
- **Fix:** every library integration is pinned to a known-compatible version and verified, and the build pipeline reviews each step before moving on — this is how we caught a styling-engine mismatch that would otherwise have surfaced only on-device.

### 10.7 "Full app for judges" without faking it
- **Challenge:** the app must look populated and real, not empty.
- **Fix:** a comprehensive, idempotent **demo seed** — real patients, appointments, prescriptions, lab reports, and pharmacy orders across every lifecycle state — so dashboards show real, computed numbers from real rows, not hardcoded values.

### 10.8 Deferred, explicitly out of scope (and why that's OK)
Messaging/chat, per-pharmacy inventory, and delivery/rider tracking are **deliberately deferred** to their own future spec — real subsystems, not faked. Naming them as *scoped-out* rather than half-building them is a maturity signal, not a gap.

---

## 11. Roadmap

1. **Now:** finish the mobile app screens against the completed backend; run the three-phone live verification + the low-end-device smoothness pass.
2. **Phase 3–4 (ML):** data annotation → train symptom→specialty / acuity models and OCR+extraction for lab reports; swap behind the frozen contract.
3. **Post-demo hardening:** Firebase Phone Auth (real OTP); deploy backend to free-tier hosting (remove LAN dependency); distribute the app via EAS build (sideload APK).
4. **Future subsystems:** in-app messaging, pharmacy inventory, delivery/rider tracking with live status.

---

## 12. The demo (what you'll show tomorrow)

Three physical Android phones on one Wi-Fi, one laptop running the backend:

1. **Patient** signs up on a new number → types "fever and cough", adds a report photo (really uploaded) → sees the routing result.
2. Tries "chest pain and breathlessness" → sees the **red emergency takeover**.
3. Picks a doctor from the list/map → books a slot.
4. **Within seconds the doctor's queue updates** on phone B.
5. Patient and doctor **join the same video room**.
6. Doctor writes a prescription → **it appears on the patient's phone**.
7. Patient consents to a pharmacy → **the pharmacy's inbox lights up** on phone C → pharmacy accepts → **patient's status flips to accepted**.

That end-to-end, cross-device, real-time loop — at zero running cost — is the demonstration.

---

## 13. Tech stack at a glance

| Layer | Technology | Why |
|---|---|---|
| Mobile | Expo / React Native, TypeScript (strict) | one codebase, native capabilities (camera, video, file picker) |
| Navigation / styling / state | expo-router / NativeWind / zustand / React Query | file-based routing, utility styling, light session store, cache-first server data + polling |
| Performance | Reanimated, FlashList, expo-image | 60fps on low-end hardware, structurally |
| Backend | FastAPI (Python), pydantic | typed, fast, clean router/service separation |
| Data | Postgres + PostGIS, Alembic | relational + geospatial (nearest-doctor), versioned migrations |
| Storage | MinIO (S3-compatible) | real report uploads, self-hosted, free |
| Triage/ML | dedicated service, deterministic stub (→ free OSS OCR/NER later) | frozen contract, swap-in models |
| Video | self-hosted LiveKit (open-source WebRTC) + backend join-token endpoint | free, self-hosted, no key/account; Cloud free-tier fallback |
| Maps | MapLibre + OpenStreetMap | free, no API key, no billing account |
| Infra | Docker Compose | one-command full stack |
| Quality | pytest, Jest + RNTL + MSW, zod contract validation | test-first, contract-safe |

---

## 14. One-paragraph abstract (for the top of your report)

> **NADI** is a zero-cost, production-grade telehealth triage platform that solves the first and hardest problem in primary care — *which doctor should I even see?* A patient describes their symptoms (in English, Hindi, or Marathi) and optionally uploads lab reports; NADI estimates how urgent the case is and which specialty fits, explains why, and escalates emergencies immediately — **without ever diagnosing.** It then carries that single case, live and in sync, across three roles — patient, doctor, and pharmacy — proving genuine cross-device coordination on real infrastructure. Built on Expo/React Native and a FastAPI + PostgreSQL/PostGIS backend, with free open-source video and maps and a swap-ready ML layer, NADI is engineered for 60fps on low-end phones, for patient-consent-driven privacy, and for the regulatory reality of Indian telemedicine.

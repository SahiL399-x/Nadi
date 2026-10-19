# NADI Backend Expansion Design (Doctor + Pharmacy portals, v2 contract)

Date: 2026-10-19
Status: Draft for review (pre-plan)
Supersedes: the §9 "frozen" API contract — this is the **v2 contract** (additive). Requires **ADR-0005**.
Builds on: merged Phase 2 backend (`9a282bd`), ADR-0003/0004, and the frontend design spec (`2026-10-19-nadi-frontend-design.md`).

## Goal

Expand the backend so the doctor and pharmacy portals in the reference mockups ("Nadi Pariksha" showcases) are backed by **real endpoints and real data** — not placeholder screens. Scope is **Core + Medium** tiers; the three Heavy subsystems (messaging, inventory, delivery/rider) are explicitly deferred to a later spec. A comprehensive **demo seed** populates every feature so the app looks full in front of judges while remaining 100% real (DB rows served by real endpoints, genuine cross-device sync).

## Decisions captured (2026-10-19)

- **Build backend first, then frontend** for the full doctor/pharmacy feature set.
- **Scope = Core + Medium**; defer Heavy (messaging, per-pharmacy inventory, delivery/rider + maps).
- **In-app video** (no browser redirect) via the **Jitsi Meet React Native SDK** (`@jitsi/react-native-sdk`) — free, public `meet.jit.si` rooms, no key/billing; needs a native dev build (already required by MapLibre).
- **Stats endpoints** added for real dashboard numbers.
- **Pharmacy stays navy** (locked palette unchanged); doctor navy, patient green.
- **Demo seed** populates all features with realistic Nashik/Maharashtra data.

## Global constraints (unchanged)

- Python: type hints, `ruff`+`black`, pydantic at boundaries; routers thin, logic in `services/` (ProjectPlan §12).
- RBAC: a doctor sees only their own patients/appointments; a pharmacy sees prescriptions routed to it, never medical history (§11).
- **The system routes, it does not diagnose** (§14.1).
- **No AI/tool attribution** in any committed artefact; commits short, imperative, lowercase (§14.11).
- **Strictly $0 / no billing**; in-app video uses public jit.si (no key).
- Every new endpoint has pydantic response models + tests; migrations via Alembic; seed is idempotent.
- Additive only — no existing shape changes, so the merged frontend core keeps working.

## Contract status — ADR-0005

The §9 contract was frozen (changes require an ADR). This expansion is large and additive. **ADR-0005 ("v2 contract — doctor/pharmacy portal endpoints")** records: the freeze is lifted for additive growth; no existing endpoint/shape changes; the new surface below is the v2 contract. First task of the first plan writes ADR-0005.

---

## 1. Data models (new + extended)

### Shared
- **`Medicine`** (new) — `id, name, strength, form` (`tablet|capsule|syrup|drops|injection`), `is_common: bool`. Backs prescription search. Seeded ~40 common Indian medicines.
- **`Consultation`** (extend) — add `scheduled_at: datetime | None` (appointment date+time; existing `booked_for` stays as the display slot string) and extend `ConsultationStatus` enum with **`ARRIVED`** (between BOOKED and IN_PROGRESS). UI mapping: `BOOKED→Upcoming`, `ARRIVED→Arrived`, `IN_PROGRESS→In Progress`, `DONE→Completed`.
- **`ConsultationNote`** (new) — `id, consultation_id, author_id, text, created_at`. Notes a doctor writes during/after a consultation.

### Doctor-side
- **`DoctorAvailability`** (new) — `id, doctor_id, weekday (0–6), morning_start, morning_end, evening_start, evening_end, is_open: bool`. One row per weekday.
- **`Doctor`** (extend) — add `clinic_address: str`, `clinic_lat/clinic_lng` (reuse `location`), `about: str | None`. Profile get/update.

### Patient medical history (Medium)
- **`PatientCondition`** (new) — `id, patient_id, label, kind` (`condition|allergy|family_history`). e.g. "Diabetes" / family_history; "No known allergies" rendered when none of kind=allergy.
- **`PatientVisit`** (new) — `id, patient_id, consultation_id | None, visited_at, summary, status`. "Latest Visit" + visit history.

### Pharmacy-side (Core)
- **`PharmacyOffer`** (extend) — expand `OfferStatus` to the full lifecycle: `TO_VERIFY, PENDING, PREPARING, VERIFIED, OUT_FOR_DELIVERY, DELIVERED, COMPLETED, CANCELLED, DECLINED`. Add `order_no: str` (human id, e.g. `NP4582`) and `items_count`/`total_inr` convenience fields (or computed). Delivery/rider tracking itself is **Heavy/deferred** — an order can reach `DELIVERED` as a status without the rider subsystem.

> Heavy/deferred models (NOT in this spec): `Message`/`Thread`, `InventoryItem`, `Delivery`/`Rider`.

---

## 2. Endpoint surface (v2 — Core + Medium)

All additive, all under `/v1`. 🟢 Core, 🟡 Medium.

### Doctor
- 🟢 `GET /v1/doctor/stats` → `{ appointmentsToday, pending, completed, prescriptionsIssued, newPatients }` (all computed from the DB for the authed doctor).
- 🟢 `GET /v1/doctor/appointments?date=YYYY-MM-DD` → `AppointmentOut[]` `{ id, patientName, patientAge, patientSex, photoUrl, time, status, acuity, complaint }`, grouped/sortable by time. Date defaults to today. (The existing `GET /v1/doctor/queue` stays for the core triage flow; appointments is the richer, dated view.)
- 🟢 `GET /v1/medicines?q=` → `MedicineOut[]` `{ id, name, strength, form }` (prefix/substring search; empty `q` returns common ones).
- 🟢 `POST /v1/consultations/{id}/notes` `{ text }` → `{ id }`; `GET /v1/consultations/{id}/notes` → `NoteOut[]` (doctor who owns the consultation, or the patient).
- 🟡 `GET /v1/doctor/patients/{patientId}` → `PatientProfileOut` `{ name, age, sex, photoUrl, conditions[], allergies[], familyHistory[], latestVisit, visits[], prescriptions[] }` (RBAC: only patients booked with this doctor).
- 🟡 `GET /v1/doctor/prescriptions?status=all|active|completed` → `PrescriptionOut[]` (issued by this doctor).
- 🟡 `GET /v1/doctor/lab-reports?status=all|pending|completed` → `LabReportOut[]` `{ id, patientName, photoUrl, date, status }`.
- 🟡 `GET /v1/doctor/availability` / `PUT /v1/doctor/availability` → `AvailabilityOut[]` (7 rows) / accepts the updated week.
- 🟡 `GET /v1/doctor/profile` / `PUT /v1/doctor/profile` → `DoctorProfileOut` `{ name, specialty, qualifications, experienceYears, clinicAddress, about, photoUrl }`.

### Pharmacy
- 🟢 `GET /v1/pharmacy/stats` → `{ newOrders, inProgress, outForDelivery, completedToday }` (computed from order statuses).
- 🟢 `GET /v1/pharmacy/orders?status=all|pending|preparing|...` → `OrderOut[]` `{ id, orderNo, patientName, phone, itemsCount, totalInr, status, placedAt }`. (The existing `GET /v1/pharmacy/inbox` stays for the core consent flow; orders is the richer board.)
- 🟢 `POST /v1/pharmacy/orders/{offerId}/status` `{ status }` → `{ status }`. Validates allowed transitions (e.g. `PREPARING→OUT_FOR_DELIVERY→DELIVERED`). Advancing to `ACCEPTED/PREPARING` flips the linked prescription status, consistent with the existing accept flow.

### Video (frontend only)
- No backend. In-app Jitsi SDK joins `meet.jit.si/nadi-{consultationId}` for both patient and doctor. (Optional future: JWT-authed private rooms — deferred.)

> Deferred (Heavy) endpoints — NOT in this spec: `/v1/messages/*`, `/v1/pharmacy/inventory*`, `/v1/pharmacy/deliveries*`.

---

## 3. In-app video (Jitsi RN SDK)

Replace the `expo-web-browser` redirect (frontend spec §4 / Plan 02 Task 12 and Plan 03) with **`@jitsi/react-native-sdk`** embedded in the Consultation screen for both patient and doctor. Same deterministic room `nadi-{consultationId}`. Requires `expo prebuild` + a dev build (config plugin), consistent with MapLibre. Camera/mic permissions handled by the SDK. Still $0 (public rooms, no key). Fallback if the SDK fails to load: an in-app error with a retry (no silent dead end). This supersedes the browser-redirect decision in the frontend spec — a frontend-spec amendment will note it.

---

## 4. Demo seed (the "full app for judges" requirement)

Extend `apps/api/seed/seed.py` (idempotent) so every feature renders full and real. All data Nashik/Maharashtra, consistent with existing seed. No hardcoded API responses — these are DB rows the real endpoints return.

- **Medicines:** ~40 common Indian medicines (Paracetamol 500mg, Amoxicillin 500mg, Amlodipine 5mg, Metformin 500mg, Pantoprazole 40mg, Cetirizine 10mg, Azithromycin 500mg, etc.) with forms.
- **Demo doctor `+915000000001`:** a full day — **8 appointments** across statuses (3 Completed, 1 In Progress, 1 Arrived, 3 Upcoming) spanning Today/Tomorrow/Sat with real patients, times, and complaints; profile (clinic address, about, qualifications); Mon–Fri availability (9–1, 5–8); **6 issued prescriptions** (→ "Prescriptions Issued 6"); **2 new patients this week**; a mix of lab reports (Completed/Pending).
- **Patients:** the existing 6 queue patients + a few more, each with medical history (conditions, allergies or "no known allergies", family history), latest visit, and visit history; consultation notes on completed visits.
- **Lab reports:** several `Report` + `LabValue` sets (anaemia, thyroid, diabetes panels) across Completed/Pending.
- **Pharmacy (`Shree Sai Pharmacy` etc.):** orders across the full lifecycle so the dashboard reads **New 12 / In Progress 8 / Out for Delivery 5 / Completed 28** (seed enough `PharmacyOffer` rows in each state), each with an `orderNo` (NP45xx), patient, items, totals.
- **Stats** then compute to match the mockup numbers from the seeded rows (not hardcoded).

Seed stays idempotent (guard on the existing `+915000000001` check) and is extended, not rewritten.

---

## 5. Sequencing (build order)

Each stage ships working, tested software.

1. **Stage A — ADR-0005 + Core doctor:** medicines + search, appointments (+`scheduled_at`/`ARRIVED`), consultation notes, doctor stats. Seed: medicines, appointments, notes.
2. **Stage B — Core pharmacy:** order lifecycle (`OfferStatus` expansion, `order_no`), orders board, order status transitions, pharmacy stats. Seed: lifecycle orders.
3. **Stage C — Medium doctor:** patient profile + history models, prescriptions list, lab-reports list, availability, profile. Seed: histories, visits, availability, lab reports, issued prescriptions.
4. **Stage D — Demo seed finalisation:** tune counts to match the mockup dashboards; verify every endpoint returns full data.

Frontend for these screens follows in extended plans (doctor/pharmacy portal plans), plus the in-app Jitsi swap — after the backend stages land.

## 6. Testing

- pytest per endpoint (auth/RBAC, shape, status transitions, date filters, stats math) following existing `apps/api/tests` patterns.
- A seed test asserting the demo counts (appointments=8, prescriptions=6, pharmacy order-state tallies) so the "full app" stays full across reseeds.
- `openapi.json` regen → `packages/shared-types` regen so the frontend types track v2.

## 7. Explicitly deferred (Heavy — later spec)

- **Messaging/chat** (threads, messages, real-time).
- **Per-pharmacy inventory** (stock levels, low/out, add/update).
- **Delivery/rider** (delivery model, rider assignment, live status, map route/ETA).

These are real subsystems, each warranting its own spec + plan when prioritised. Their mockup screens are **not** built or faked in this scope.

---

## Open items for reviewer

- Confirm the v2-contract/ADR-0005 approach (lifting the §9 freeze for additive growth).
- Confirm the demo-seed dashboard targets (8 appts / 6 prescriptions / pharmacy 12-8-5-28) or adjust.
- Confirm in-app Jitsi SDK (accepting the native dev-build requirement) over the browser redirect.

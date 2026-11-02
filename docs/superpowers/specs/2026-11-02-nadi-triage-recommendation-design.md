# NADI Triage Model + Doctor Recommendation System — Design Spec

**Date:** 2026-11-02
**Status:** Approved design, pre-plan
**Supersedes the triage portions of:** `nadi-ml-approach` Workstream B notes (the "2 open items" are resolved here).

## Context

NADI routes a patient's symptom description to the right medical specialty and then to
doctors. Today that routing is a **keyword stub** (`apps/ml-service/app/triage_stub.py`) that
returns an `acuity` level, a `specialties` list, `drivers`, and `redFlags`. Two problems drove
this redesign:

1. **The mentor (AIML) wants a *trained* model**, visibly trained — not hand-coded keyword
   rules. This is the showpiece deliverable.
2. **Patients search lazily** — single words like "Headache", "Cold", "Dizzy", "Diabetes" —
   and often in **Hinglish/Hindi**. A model asked to route a single bare word gives a vague,
   low-confidence answer, and a doctor's own fine-grained expertise (finer than ~10
   specialties) is invisible to the system.

The outcome this spec commits to: a **combined recommendation system** where (a) doctors
build a Fiverr-style profile with self-selected **keywords**, (b) a patient query is matched
against those keywords first (ranked by rating) as a fast path, and (c) a **trained BiLSTM**
maps messier/vague/multilingual free-text to a specialty as the ML fallback. Separately, the
product decision was made to **remove `acuity` and red-flags from the entire app** — the model
and the app route to a specialty only; there is no urgency signal anymore.

**Scope is large and deliberately one spec** (user decision): ML notebook + ONNX serving +
doctor keyword field + profile editor + recommendation engine + patient search bar + the
acuity teardown. The implementation plan will be split into multiple phase plans; each phase
is independently testable.

## Locked decisions

| Decision | Choice | Rationale |
|---|---|---|
| Overall framing | One combined recommendation system | User decision; keyword fast-path + ML fallback is one coherent flow |
| Model deliverable | Colab notebook, runs top-to-bottom on free T4 | Mentor watches it train |
| Model target | **Specialty** (softmax over NADI's ~10 seeded specialties) | The two datasets have disjoint disease labels; specialty is the shared label, and it lets the model train on the multilingual rows |
| Architecture | TF-IDF + LogReg **baseline** → **BiLSTM** advanced | "RNN logic" showpiece; BiLSTM reads both directions, strong on short sequences |
| Data | **Hybrid**: `gretelai/symptom_to_diagnosis` (English, Apache-2.0, 22 dx) + `Tulsiandhare/Multilingual_medical_symptom_triage` (real Hindi/Hinglish rows) | gretelai gives clean license + specialty spread; Tulsiandhare gives real code-mixed text, replacing the brittle hand-built lexicon |
| Multilingual | Learned from real Hinglish/Hindi training rows + a thin normalizer | Replaces the planned hand-built romanized-Hindi lexicon |
| Serving | Train Keras on GPU → export **ONNX** → **onnxruntime** CPU in ml-service, lazy-loaded behind `ML_TRIAGE_ENABLED` (default OFF) | Train heavy on GPU, serve light (~50MB) on any free host; a tiny model over one sentence is <5ms on CPU |
| Keyword matching | Normalized token/substring + small synonym map (v1); ranked by **rating** | Handles lazy single-word queries without the ML; doctor's fine-grained expertise |
| Acuity | **Removed entirely** (acuity level + red-flags) across ml-service/api/mobile/DB | Product decision; routes, does not diagnose; no urgency signal |
| Doctor queue order (post-teardown) | By `booked_for` ascending | Replaces emergency-first `_ACUITY_ORDER` |
| Gaming mitigation | Cap keywords (≤15), lean on existing `is_verified` | Self-tagging can be abused; demo-adequate |

## Non-goals

- Individual-doctor relevance ranking beyond keyword/specialty match + rating + distance.
- A real OTP / auth change (out of scope; demo stub stays).
- Endocrinology/Gastroenterology etc. as new specialties — keywords provide the fine grain
  on top of the existing ~10 seeded specialties; no new specialty rows.
- Retraining infrastructure / online learning. The notebook trains once; artifacts are shipped.
- Production-grade dataset licensing of Tulsiandhare (see Risks — a gate, not a goal).

---

## Phase 1 — The training notebook (mentor showpiece)

**Location:** `apps/ml-service/notebooks/triage_rnn.ipynb` (committed; Colab-runnable).

**Cells, in order:**
1. **Setup** — install `datasets`, `scikit-learn`, `tensorflow`, `tf2onnx`; imports; set seeds.
2. **Load data** —
   - `gretelai/symptom_to_diagnosis` (loads without auth). Columns: symptom text + `label`
     (22 diagnoses).
   - `Tulsiandhare/Multilingual_medical_symptom_triage` — use `patient_query`, `disease`/
     `category`, and `language` ∈ {English, Hindi, Hinglish}. **Loaded at runtime only; the raw
     dataset is NOT committed** (see Risks).
3. **Disease→specialty maps** — two hand-authored dicts (one per dataset's disease/category
   vocab) → NADI's seeded specialties: General Physician, General Medicine, Cardiology,
   Dermatology, ENT, Gynaecology, Paediatrics, Orthopaedics, Haematology. (Emergency Medicine
   is dropped with acuity — do not map to it.) Print any unmapped label as a loud assertion so
   the map stays complete.
4. **Normalize + unify** — lowercase, strip, collapse whitespace; map each row to its specialty
   label; union both datasets into one multilingual training frame. Show class balance and a
   few Hindi/Hinglish examples with their mapped specialty.
5. **Baseline** — TF-IDF + LogisticRegression; report accuracy, macro-F1, confusion matrix on a
   held-out split.
6. **BiLSTM** — Keras `TextVectorization` → `Embedding` → `Bidirectional(LSTM)` → `Dense`
   (softmax over the specialty classes). Train with a validation split; **plot loss/accuracy
   curves** (the "watch it train" moment). Early stopping.
7. **Compare** baseline vs BiLSTM on the test split; show a few live predictions incl. a terse
   word ("nausea") and a Hinglish phrase ("mujhe ulti jaisa lag raha hai").
8. **Bonus** — report disease-level accuracy on the gretelai subset (we still have its fine
   labels) to show "the model also implies a plausible disease."
9. **Export artifacts** → `apps/ml-service/app/triage_model/artifacts/`:
   - `triage_bilstm.onnx` (via `tf2onnx`), with the `TextVectorization` either baked into the
     exported graph or exported as a vocab JSON consumed by `infer.py` (decide at build time;
     prefer baking vectorization in so serving needs no Keras).
   - `specialty_labels.json` — index→specialty name.
   - `normalizer.json` — the thin multilingual normalization resource (if any survives beyond
     lowercase/whitespace once the model trains on real multilingual data).
   - `model_card.md` — dataset provenance, metrics, intended use, "routes not diagnoses".

**Testing:** the notebook asserts both models train and that sentinel symptoms (incl. one
Hinglish) map to sane specialties. Not in CI; the *exported artifacts* get a smoke test in
Phase 2.

---

## Phase 2 — ml-service serving (ONNX, flag-gated)

**New package** `apps/ml-service/app/triage_model/` (mirrors the `ocr/` package shape):
- `normalize.py` — the shared query normalizer (lowercase/whitespace + optional lexicon). Used
  by both serving and, conceptually, the recommendation keyword match.
- `infer.py` — **lazy-loads** the onnxruntime session + labels + vectorization on first use; a
  module-level singleton. `predict(text) -> list[{name, score}]` top-k specialties.
- `pipeline.py` — `run(symptom_text, labs, age, sex) -> dict` producing the new contract;
  never raises (fallback to a safe default specialty on any error, like the OCR pipeline).

**Flag:** `ML_TRIAGE_ENABLED` (default **OFF**), mirroring `ML_OCR_ENABLED`. OFF = the keyword
stub (minus acuity, see Phase 4). ON = the BiLSTM.

**New `/triage` contract (specialty-only):**
```json
{ "specialties": [{"name": "Cardiology", "score": 0.74}, ...],
  "labs": [...],
  "modelVersion": "triage-bilstm-v1" }
```
Dropped vs today: `acuity`, `acuityConfidence`, `redFlags`, `drivers`.

**Dependencies:** add `onnxruntime` to the ml-service container. **Do not** add tensorflow to
the container (training is Colab-only).

**Testing (TDD):** flag-off returns stub shape (specialty-only); flag-on returns a real
specialty for a known English symptom and for a Hinglish symptom; artifact smoke test loads the
ONNX and runs one inference.

---

## Phase 3 — Doctor profile keywords (Fiverr-style)

**DB:** migration adds `keywords: ARRAY(String)` to `doctors` (default empty). No other new
columns — `about`, `qualifications`, `experience_years`, `rating`, `review_count`,
`is_verified`, `languages`, `fee_inr` already exist.

**api:** extend `DoctorProfileIn`/`DoctorProfileOut` and `doctor_service.update_profile` to read
and write **keywords** (normalized, de-duplicated, **capped at 15**), plus make
**qualifications** and **experience_years** editable (the "certifications/experience" the
Fiverr vision calls for). `GET/PUT /v1/doctor/profile` already exist.

**mobile:** the doctor profile editor (`app/(doctor)/profile` area + `doctorPortal` api/hook)
gains a keyword chips input (add/remove, cap enforced) and fields for qualifications +
experience. `DoctorProfileOut` consumers updated.

**Testing (TDD):** api — round-trip keywords through PUT/GET; cap enforced; normalization/dedupe.
mobile — editor renders + submits keywords; schema parse.

---

## Phase 4 — Recommendation engine + patient search (query → ranked doctors)

**api service** `recommend(db, query, specialty, lat, lng, radius_km, lang)` in
`doctor_service` (or a new `recommend_service`):
1. **Normalize** the query (shared normalizer; Hinglish/Hindi → English where the lexicon
   applies).
2. **Keyword fast-path:** doctors whose `keywords` array matches a normalized query token
   (PostgreSQL `ARRAY` overlap / `ANY`, plus a small synonym map). Rank by **rating desc**,
   then `review_count`, then distance. Geo radius still applies.
3. **ML fallback:** if the keyword set is empty, use the provided `specialty` (from the RNN at
   intake, or from a direct `/triage` call for a free-text search) → existing specialty filter,
   ranked by distance then rating.
4. **Merge + dedupe**, demo doctor pinned (preserve `_demo_doctor` behavior).

**Endpoint:** extend `GET /v1/doctors` with an optional **`q`** param (the raw query). When `q`
is present, `search()` routes through `recommend()`; when absent, current specialty/geo behavior
is unchanged (back-compat).

**RNN stays visibly in the loop:** at `intake`, the BiLSTM still predicts the specialty stored
on the consultation and shown on the result screen ("Suggested: Cardiology"). The doctor list
for that consultation calls `recommend(symptomText, predictedSpecialty)` — keyword hits first,
specialty fallback behind. A **new patient doctor-search bar** calls the same path with a typed
`q`.

**mobile:** add a search bar on the doctor-list/result screen; wire `q` through the doctors api
+ hook; render keyword-matched doctors (rating-sorted) above specialty matches.

**Testing (TDD):** api — keyword hit returns rating-sorted doctors; no hit falls back to
specialty; `q` absent = unchanged behavior; demo pin preserved. mobile — search bar drives the
query; list renders ordered.

---

## Phase 5 — Acuity teardown (app-wide)

Remove the `acuity` level and red-flags everywhere; specialty-only throughout.

- **ml-service:** delete `app/redflags.py`; `triage_stub.py` returns specialty-only (no
  `acuity`/`acuityConfidence`/`redFlags`), so the flag-OFF path matches the new contract too;
  update `tests/test_triage_stub.py`.
- **api:**
  - Migration **0010** — drop columns `acuity`, `acuity_confidence`, `red_flags`, **and
    `drivers`** from `triage_results`; drop the `acuity` Postgres enum type.
  - `app/models/triage.py` — remove the `Acuity` enum + those columns.
  - `app/schemas/common.py` — `TriageResultOut` drops `acuity`, `acuityConfidence`, `drivers`,
    `redFlags`; `from_model` updated; remove the `Acuity`/`Driver` types if unused elsewhere.
  - `app/schemas/appointment.py` + `app/schemas/consultation.py` — drop acuity fields from
    `QueueItemOut`/`AppointmentOut`.
  - `app/services/consultation_service.py` — remove `_ACUITY_ORDER`; **queue + appointments
    order by `booked_for` ascending**; `intake` no longer writes acuity/red_flags.
  - `seed/seed.py` — stop writing acuity/red_flags.
- **mobile:**
  - Delete `src/components/ui/AcuityBadge.tsx` + its test; remove from `ui/index.ts`.
  - Strip acuity from `QueueRow.tsx`, `AppointmentRow.tsx`, `app/(patient)/result.tsx`,
    `src/api/schemas.ts`, `src/api/doctorPortal.ts`, and `packages/shared-types/src/types.ts`.
  - Update affected tests (`useQueue`, `useTriage`, `schemas`, `NadiNote`, etc.).
- **theme:** acuity color tokens in `src/theme/tokens.ts` may be removed if unused after the
  badge is gone.

**Testing:** api + mobile suites updated to the specialty-only contract; new queue-ordering
test (booked-time asc); full docker stack + the E2E flow script green after the contract change.

---

## Data flow (end state, `ML_TRIAGE_ENABLED=true`)

```
Patient types "Headache" / "mujhe bukhar hai" / "nausea and chest burning"
        │
        ▼
  intake → /triage (ml-service)
        │          └── BiLSTM(ONNX) → predicted specialty (always; shown on result screen)
        ▼
  GET /v1/doctors?q=<text>&specialty=<predicted>
        │
        ├── keyword match on doctors.keywords?  ──yes──▶ those doctors, ranked by rating
        │
        └── no ──▶ doctors of predicted specialty, ranked by distance/rating
        │
        ▼
  merged + deduped, demo doctor pinned → doctor list + map
```

## Risks / gates

- **Tulsiandhare license is unstated** ("research purposes only", synthetic). **Gate:** verify
  the license before shipping any derived artifact; do not commit the raw dataset (load at Colab
  runtime); add a NOTICE/attribution entry if required — same discipline applied to the
  NidaanKosha vocab (`DATASET_REGISTER.md`). If the license is incompatible, fall back to
  gretelai-only training + the hand-built Hinglish lexicon for the multilingual path.
- **Synthetic data quality** — report metrics honestly in the model card; the in-app value is
  routing, framed as a suggestion for doctor review.
- **Breaking contract change** (dropping acuity/drivers/redFlags) touches shared-types + mobile
  schemas + api + DB together — Phase 5 must land as one coherent change; run the full stack +
  E2E script after.
- **ONNX export of `TextVectorization`** can be fiddly; if baking it into the graph fails,
  export the vocab to JSON and reproduce the vectorization in `infer.py` (documented fallback).
- **Removing red-flags removes the only emergency safety net** — an accepted, deliberate product
  decision recorded here.

## Verification (end to end)

1. Phase 1: run the notebook top-to-bottom on Colab; both models train; curves plotted;
   artifacts exported.
2. Phase 2: `apps/ml-service` pytest (flag-off shape, flag-on real + Hinglish, artifact smoke).
3. Phase 3/4: `apps/api` pytest (profile keyword round-trip + cap; recommend keyword-hit vs
   fallback; `q`-absent back-compat); mobile jest (editor + search bar).
4. Phase 5: full `apps/api` + ml-service + mobile suites green on the specialty-only contract;
   queue-ordering test.
5. Whole stack: `docker compose up`, run `scratchpad/e2e_flow.py`-style flow with
   `ML_TRIAGE_ENABLED=true` → intake routes a terse + a Hinglish query to sane doctors.

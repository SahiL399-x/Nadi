# NADI ML — Workstream A: Lab-report OCR (design)

**Date:** 2026-10-25
**Status:** Approved (design); pending spec review before planning.
**Source of truth for the ML program:** `NADI_ML_Implementation_Blueprint.pdf` (reviewed 2026-10-25).

---

## 0. Program context (why this spec is scoped to OCR only)

The ML work is three independent subsystems. Each gets its own design → plan → build cycle,
executed in sequence so no single spec tries to hold all of them:

1. **Workstream A — Lab-report OCR** ← *this spec, built first.*
2. **Workstream B — Multilingual symptom understanding + specialty ranking** (later).
3. **Workstream C — Pharmacy dispatch optimization** (later; ETA regression deferred — the data
   to train it does not exist. `PharmacyOffer` has no delivery-event timestamps.).

**Decisions that frame the whole program (from brainstorming 2026-10-25):**
- Target is a **production** app, not the demo. Quality bar is high; "$0 demo" constraint is lifted,
  but we still build/benchmark on synthetic + public data only.
- Build locally first on the dev laptop (**Windows 11, RTX 3050, ~4 GB VRAM**); the production
  inference host is deferred, so **models stay lightweight** to keep CPU and GPU options open.
- **No clinician is currently attached.** This blocks only the *supervised* specialty classifier in
  Workstream B. It does **not** affect OCR, whose correctness is graded against ground-truth text,
  not medical judgement. Any clinical-correctness or accuracy claim requires medical sign-off; until
  then the system is framed as "a suggestion for a doctor to review" (aligned with India's
  Telemedicine Practice Guidelines 2020 and the existing product stance).
- **Non-negotiables carried from the blueprint:** reuse existing architecture; additive /
  feature-flagged contract changes only; no fabricated results; synthetic/de-identified data only;
  keep the deterministic red-flag safety layer; never log raw report content.
- **Compute/training policy (operator preference):** use the GPU fully — OCR runs in **GPU
  inference** mode on the 3050 for the service + benchmark (not CPU). Where training/fine-tuning
  actually occurs (conditionally here, and in Workstream B), **train to convergence — no artificial
  under-training**: full epochs with proper early-stopping, model sized to the task. The binding
  limit is **VRAM (~4 GB)** and available labelled data, not compute willingness; if a model needs
  more than 4 GB, flag it for the stronger-GPU/cloud option rather than silently under-training.
  Note: Workstream A (OCR) is pretrained-inference + benchmark — there is nothing to train unless the
  benchmark justifies a fine-tune on a legally-usable labelled image set.

### Baseline verified in code (Phase 0 audit, 2026-10-25)

| Item | Reality in the repo |
|---|---|
| ML service | Real FastAPI container `apps/ml-service`, `python:3.11-slim`, behind `ml_client.py`. Endpoints `/ml/v1/{health,symptom,document,triage}`. |
| OCR seam | `document_stub.extract(object_key) -> list[LabValue dict]`; called by `apps/api/app/services/consultation_service.py:49` via `ml_client.document(object_key)`. |
| Current `document` response | `{"labs": [ {analyte, value, unit, refRange, flag∈{L,N,H}} ]}`. |
| Storage of output | Extracted labs stored in `triage.labs` (JSONB); `Report.ocr_status` (`consultation.py:42`) flips `pending`→`done`. |
| ML service storage access | **None today** — only receives `objectKey`, no MinIO/S3 creds or client. |
| Report storage | MinIO; API signs presigned upload URLs (`storage_service.py`), bucket `nadi-reports`. |
| Host Python | 3.13 (benchmark scripts need a 3.11/3.12 venv); the **service container is 3.11**, so OCR deps are unaffected by host version. |

---

## 1. Objective

Replace the filename-keyword `document_stub` with a real OCR pipeline that extracts structured lab
fields from an uploaded report image, with measured accuracy, safe fallbacks, and a backward-compatible
contract. Deliver an honest, reproducible benchmark instead of a claimed accuracy number.

## 2. Architecture

New `ocr/` package inside `apps/ml-service/app/`, following the blueprint's module boundaries:

| Module | Responsibility |
|---|---|
| `ocr/storage.py` | Fetch object bytes from MinIO **by key**, read-only creds. Minimum-access. |
| `ocr/preprocess.py` | Validate file type/size; orient/deskew/contrast only when useful; reject corrupt/unsupported safely. Preserves the original. |
| `ocr/engine.py` | PaddleOCR wrapper. Model loaded **once per worker** (lazy singleton). Returns text + boxes + confidence. |
| `ocr/parse.py` | Group OCR boxes into rows/cells → raw fields: test name, value, unit, printed reference interval, optional date/specimen. |
| `ocr/normalize.py` | `lab_normalizer`: alias dictionary + structured vocabulary → canonical analyte; unit-compatibility check; compute `flag` (L/N/H) from value vs parsed ref range. **Never infers missing units/ranges**; flags ambiguity instead of guessing. |
| `ocr/pipeline.py` | `extract_report(object_key) -> structured result`. Orchestrates the above. |

The image-bytes access pattern is **"ML service reads MinIO by key"** (chosen): the ML container gets
read-only S3 creds via env; the existing `document(objectKey)` contract is unchanged; bytes never
round-trip through the API.

### Model choice

- **PaddleOCR 3.x, PP-OCRv5 lightweight (mobile) detection + recognition.** Runs in **GPU mode on the
  3050** for dev + benchmark, but kept **CPU-runnable** so the deferred production-host choice stays
  open. **Not** PaddleOCR-VL (does not fit 4 GB VRAM comfortably; overkill for a first baseline).
- **PP-StructureV3 table parser is conditional** — added only if plain OCR + geometric row-grouping
  underperforms on the benchmark (measure before adding the dependency).
- Exact model variant + pinned version decided **after** verifying the current official PaddleOCR
  release and Python-3.11 wheel availability at build time (blueprint R1/R2).

## 3. Contract (strictly additive)

`document()` keeps returning `labs` byte-compatibly, and **adds** richer structure. Existing consumers
(`consultation_service`) read only `labs` and are unaffected.

```jsonc
{
  "labs": [ { "analyte": "...", "value": 9.1, "unit": "g/dL", "refRange": "12.0 - 15.5", "flag": "L" } ],
  // --- added ---
  "fields": [
    {
      "testNameRaw": "HAEMOGLOBIN", "testNameNormalized": "Haemoglobin",
      "valueRaw": "9.1", "valueNumeric": 9.1, "unit": "g/dL",
      "referenceRangeRaw": "12.0 - 15.5", "flag": "L",
      "sourceRegion": [x, y, w, h], "qualityFlags": ["low_confidence"?]
    }
  ],
  "needsReview": true,
  "warnings": ["unit_mismatch:..."],
  "modelVersion": "paddleocr-ppocrv5-<pin>",
  "latencyMs": 1234
}
```

`labs` is derived from the normalized `fields` (keeps the `{analyte,value,unit,refRange,flag}` shape).

## 4. Feature flag + safe fallback

- `ML_OCR_ENABLED` env, **default off**. Off → current stub (running app/demo keeps working).
- On → real OCR. If the engine fails to load, or a file errors, return `needsReview=true` with empty
  `fields`/`labs` rather than raising — the consultation flow must never crash on a bad image.

## 5. Human-in-the-loop (production)

Low-confidence fields or unit/numeric ambiguity set `needsReview=true`. The backend stores the
structured `fields` + a review status so an authorized doctor can later confirm/correct them beside the
original image. **Corrections are stored separately and never auto-become training labels.** The doctor
review *screen* is a later mobile task; this spec only guarantees the backend captures the data.

## 6. Privacy & safety

- Read-only MinIO creds in the ML service; least privilege.
- Reject unsupported/oversized/corrupt files with a clear error.
- **Never log raw report content** — log only metadata (object key hash, sizes, timings) + a
  correlation id. Store the minimum necessary.
- The deterministic red-flag layer (`redflags.py`) is untouched.

## 7. Benchmark harness (separate from the production path)

`apps/ml-service/bench/ocr_eval.py` — standalone, not imported by the service. Runs over a fixed test
manifest (the **Eka Care Medical Records Parsing Validation Set**, 288 images, test-only) and reports:
CER/WER, field exact-match, numeric accuracy, unit accuracy, test-to-value pairing, latency, and
CPU/RAM/VRAM usage — saved as JSON + per-error-type samples. **No fine-tuning on the test set.**

Supporting docs: `docs/ml/DATASET_REGISTER.md` and `docs/ml/MODEL_CARDS.md` recording exact URL, access
date, version, license (Eka sets are CC-BY-SA-4.0 → benchmark-only; PaddleOCR Apache-2.0), splits and
obligations. Dataset download uses the operator's own `huggingface-cli login` (token never in the repo),
and only if the dataset is gated.

This harness is where honest, reproducible accuracy numbers come from — not a claimed figure.

## 8. Dependencies & packaging

- Add to `apps/ml-service`: `paddleocr`, `paddlepaddle` (CPU wheel), `pillow`,
  `opencv-python-headless`, `boto3`. Pin exact versions after a smoke test.
- Dockerfile adds system libs PaddleOCR/OpenCV need (`libgl1`, `libglib2.0-0`). Image grows to
  ~1–2 GB (acceptable for a dedicated ML service; note cold-start, load model once per worker).
- `infra/docker-compose.yml`: pass read-only S3 creds + bucket + `ML_OCR_ENABLED` to `ml-service`.

## 9. Testing

- **ML-service unit tests** use a **fake OCR engine** (real Paddle is too heavy/slow for unit tests —
  exercised only in the benchmark): `preprocess` validation (reject bad file), `parse` (rows→fields on
  fixed synthetic OCR output), `normalize` (alias + unit + flag), `needsReview` logic,
  fallback-on-engine-failure, and backward-compat `labs` shape.
- **API tests**: `document()` still returns `labs`; the consultation flow stays green.
- Existing api + ml-service suites remain green.

## 10. Exit gates (this workstream)

- Benchmark script runs on sample images and the Eka set (or blocked-with-reason if the dataset is
  gated and access is pending); results stored as JSON.
- `ML_OCR_ENABLED=on` path returns the additive contract; `off` path identical to today.
- All unit/API tests green; no raw report content logged.
- `DATASET_REGISTER.md` + `MODEL_CARDS.md` populated with licenses/versions.
- No accuracy claim made beyond what the stored benchmark output supports.

## 11. Open items (tracked, non-blocking)

- Exact PaddleOCR model variant + Python-3.11 wheel verification (do at build time).
- Production inference host / GPU decision (deferred; models kept lightweight so both stay open).
- Doctor "review extracted fields beside image" screen = a later mobile workstream.
- Whether the Eka datasets are gated (determines if the HF login is needed at all).

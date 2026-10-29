# Model Cards

## PaddleOCR PP-OCRv5

- **Model**: PaddleOCR PP-OCRv5 (detection + recognition pipeline)
- **License**: Apache-2.0
- **Model card / source**: https://github.com/PaddlePaddle/PaddleOCR
- **Installed versions** (pinned in `apps/ml-service/pyproject.toml`, verified against the official PaddleOCR GitHub in Task 7):
  - `paddleocr==3.7.0`
  - `paddlepaddle==3.2.0` (CPU wheel in the container)
- **Runtime**:
  - **Container (CPU)**: `apps/ml-service` Docker image — `python:3.11-slim`, CPU-only `paddlepaddle` wheel. This is the production/demo runtime behind `app/ocr/engine.py`, gated by `ML_OCR_ENABLED`.
  - **Dev GPU (3050)**: a separate Python 3.11/3.12 host venv with the GPU `paddlepaddle` wheel installed per the official install matrix, used only for benchmark runs (see `apps/ml-service/bench/README.md`). Never used to train/fine-tune on benchmark-only data.
- **Task in this pipeline**: text line detection + recognition over lab-report images; output lines (`text`, `box`, `conf`) are consumed by `app/ocr/parse.py` and `app/ocr/normalize.py` to produce structured lab fields.
- **Known limitations**: general-purpose OCR, not fine-tuned on Indian lab-report layouts; accuracy on handwritten entries, low-contrast scans, and non-Latin scripts is unverified until a real benchmark run completes.

## Results

_Do not fill in numbers here from memory, estimation, or a partial/manual spot-check. This section is populated only by copying metrics out of a stored benchmark JSON file. Each entry must cite the JSON file and the date it was generated._

### Eka validation set — rubric-derived (real benchmark)

- **Dataset**: `ekacare/medical_records_parsing_validation_set` (gated; lab-report subset). 218 images on disk → 202 rows with gold tests, **1906 gold tests** total.
- **Model actually served**: **PP-OCRv6_medium** detection + recognition. NOTE: although this card and `pyproject.toml` were written against "PP-OCRv5", `paddleocr==3.7.0` resolves the default pipeline to the **PP-OCRv6_medium** official models (confirmed in the run log — `PP-OCRv6_medium_det` / `PP-OCRv6_medium_rec`). Treat "PP-OCRv5" references as the intended baseline; v6_medium is what ran.
- **Pipeline**: `run_ocr` → `parse_fields` → `normalize_fields`, **UNCHANGED** (no test-set adaptation — this is the clean baseline before any vocab/parser expansion).
- **Runtime**: `nadi-ml-gpu` image (paddlepaddle-gpu 3.2.0, cu126) on RTX 3050. 218 images in **857s (~3.9s/image)**, 0 per-image errors.
- **Metrics** (`score_eka.py`; see `method` in the JSON):

| Metric | micro % | macro % | What it measures |
|---|---|---|---|
| `ocr_name_in_text`  | 80.2 | 87.1 | Gold test **name** appears in raw recognized text (OCR recognition) |
| `ocr_value_in_text` | 92.5 | 95.6 | Gold **value** appears in raw recognized text (OCR recognition) |
| `name_recall`       | 38.7 | 47.6 | A **parsed field** matches the gold name (recognition + parse) |
| `value_recall`      | 35.0 | 43.5 | A name-matched parsed field also has the right value (end-to-end) |

- **Key finding**: the large gap between **recognition** (`ocr_name_in_text` 80.2%) and **extraction** (`name_recall` 38.7%) means the loss is in the **parser + alias dictionary, not the OCR engine**. PP-OCRv6 reads the reports well; the structured-field extraction is the bottleneck. This directly motivates the Step-2 expansion (NidaanKosha LOINC vocab + clustering-based row grouping).
- **Source JSON**: `apps/ml-service/bench/results/eka_baseline.json`
- **Date**: 2026-10-29

#### Step-2 Fix #1 — adaptive row grouping (`parse.py`)

- **Change**: replaced the fixed 14px row-grouping bucket with resolution-adaptive clustering (row tolerance scales with the median OCR text height). Pure geometry — **not tuned on the Eka gold** (honors the no-contamination rule). Root cause: on ~4000px scans a logical row's cells sit ~30px apart and the 14px bucket split name from value, so both were dropped (62 images parsed 0 fields despite good OCR). Covered by 2 regression tests in `tests/test_parse.py`; 35/35 ml-service tests green.
- **Same 218 images / 1906 gold tests, same PP-OCRv6_medium pipeline.** Recognition unchanged (as expected — only parsing changed), so the deltas are cleanly attributable to the fix:

| Metric | baseline micro/macro | fix #1 micro/macro | Δ micro/macro | tests gained |
|---|---|---|---|---|
| `ocr_name_in_text`  | 80.2 / 87.1 | 80.2 / 87.1 | — / — | — |
| `ocr_value_in_text` | 92.5 / 95.6 | 92.5 / 95.6 | — / — | — |
| `name_recall`       | 38.7 / 47.6 | **45.8 / 57.0** | +7.1 / +9.4 | 737 → 873 (+136) |
| `value_recall`      | 35.0 / 43.5 | **41.8 / 52.3** | +6.8 / +8.8 | 667 → 797 (+130) |

- **Remaining gap** (recognition ~80% vs extraction ~46%) is now dominated by **non-numeric/qualitative values** (urinalysis `NIL`/`PALE YELLOW`, vision `6/6`), fused value+unit cells, and column-structured layouts — the `_NUM`-only value detector drops these by design (candidate Step-2 Fix #2).
- **Source JSON**: `apps/ml-service/bench/results/eka_fix1_rowgroup.json`
- **Date**: 2026-10-29

### Synthetic fixture — `bench/ocr_eval.py` (CER/pairing harness)

_Separate harness with field-level gold; not yet run on a real dataset._

| Dataset | n | numeric_accuracy | unit_accuracy | pairing_accuracy | cer | mean_latency_ms | Source JSON | Date |
|---|---|---|---|---|---|---|---|---|
| _(none yet)_ | | | | | | | | |

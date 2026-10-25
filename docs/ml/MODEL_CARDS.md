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

_Intentionally left empty. Do not fill in numbers here from memory, estimation, or a partial/manual spot-check. This section is populated only by copying metrics out of a stored benchmark JSON file produced by `bench/ocr_eval.py` (e.g. `results/eka.json`), per the procedure in `apps/ml-service/bench/README.md`. Each entry must cite the JSON file and the date it was generated._

| Dataset | n | numeric_accuracy | unit_accuracy | pairing_accuracy | cer | mean_latency_ms | Source JSON | Date |
|---|---|---|---|---|---|---|---|---|
| _(none yet)_ | | | | | | | | |

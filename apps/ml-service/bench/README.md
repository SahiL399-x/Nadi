# OCR benchmark

## Fixture run (no dataset, no GPU)
    python bench/ocr_eval.py bench/fixtures/manifest.json

## Full Eka Care benchmark (288 images)
The Eka Care Medical Records Parsing Validation Set is test-only and may be gated.
1. On your machine: `hf auth login` (read token; never commit it). Verify with
   `hf auth whoami`. (On huggingface_hub >= 1.0 the old `huggingface-cli` command
   was renamed to `hf`; if `hf` is missing, `pip install -U huggingface_hub`.)
2. Download the dataset per its HF card into `bench/data/eka/` (DO NOT COMMIT the data).
3. Build a manifest mapping each image_path to its ground-truth fields.
4. GPU run on the dev 3050: create a Python 3.11/3.12 venv and install the GPU
   PaddlePaddle wheel per the official install matrix, then:
       python bench/ocr_eval.py bench/data/eka/manifest.json results/eka.json
5. Record the metrics in docs/ml/MODEL_CARDS.md. NEVER fine-tune on this test set.

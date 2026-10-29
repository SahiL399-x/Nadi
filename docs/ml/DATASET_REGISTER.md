# Dataset Register

Tracks every external dataset touched by the NADI ML/OCR workstream: where it
came from, under what license, and what we are allowed to do with it.

All three datasets below are from Eka Care on HuggingFace. Access requires the
operator's own `huggingface-cli login` (personal read token). The token is
**never committed or hardcoded** anywhere in this repo.

| Name | URL | Access date | License | Gated? | Modalities | Split | Allowed use |
|---|---|---|---|---|---|---|---|
| Eka Care Medical Records Parsing Validation Set | https://huggingface.co/datasets/ekacare/medical-records-parsing-validation-set | TBD (recorded at first download) | CC-BY-SA-4.0 | Yes (HF gated, requires accepted terms) | Images (lab report scans) + ground-truth fields | Test only — 288 images | **Benchmark-only. Do not redistribute derived data.** Used solely to compute OCR accuracy metrics (Task 8 harness); never used for training or fine-tuning. |
| NidaanKosha-100k-V1.0 | https://huggingface.co/datasets/ekacare/NidaanKosha-100k-V1.0 | 2026-10-29 | CC-BY-SA-4.0 | No (public) | Structured lab readings (test_name, value, unit, LOINC, ranges); 6.8M rows / 100k reports; **no images** | N/A (reference/lookup) | **Normalization-only.** Used offline (`scripts/build_analyte_vocab.py`) to build the analyte vocabulary `app/ocr/data/analyte_vocab.json` (LOINC-anchored synonym→canonical map) loaded by `app/ocr/normalize.py`. **The derived vocab IS committed** (operator decision 2026-10-29) under CC-BY-SA-4.0 with attribution — see `app/ocr/data/analyte_vocab.NOTICE.md`. Not used for training. The source parquet shards are NOT committed. |
| Eka-IndicMTEB | https://huggingface.co/datasets/ekacare/Eka-IndicMTEB | TBD (recorded at first download) | CC-BY-SA-4.0 | Yes (HF gated) | Text (Indic-language embedding benchmark tasks) | Benchmark splits per MTEB task | **Benchmark-only, do not redistribute derived data.** Reserved for future concept/embedding evaluation; not currently wired into any pipeline. |

## Process for adding a dataset

1. Record name, canonical URL, license, and gate status here before any code
   references it.
2. Access only via the operator's own authenticated `huggingface-cli login` —
   never embed a token in code, config, or CI.
3. Downloaded data lives under `apps/ml-service/bench/data/<name>/` (or
   equivalent) and is **gitignored** — never committed.
4. Mark the allowed use explicitly (benchmark-only / normalization-only /
   training-eligible). Default to the most restrictive reading of the
   license until confirmed otherwise.
5. Never fine-tune a model on a test/validation-only split.

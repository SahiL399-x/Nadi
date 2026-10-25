"""Run OCR extraction over a manifest and print/save metrics.
Usage: python bench/ocr_eval.py <manifest.json> [out.json]
Manifest entries: {"image_path": "...", "truth": [{analyte,value,unit,flag}]}.
Real runs use the PaddleOCR engine; fixtures may inline pre-computed `lines`."""
import json
import sys
import time

from app.bench_eval import evaluate
from app.ocr.engine import run_ocr
from app.ocr.preprocess import load_and_validate
from app.ocr.storage import fetch_object  # noqa: F401 (available for key-based manifests)


def _ocr_from_path(path: str):
    with open(path, "rb") as fh:
        return run_ocr(load_and_validate(fh.read()))


def main() -> None:
    manifest = json.load(open(sys.argv[1]))
    use_engine = all("lines" not in item for item in manifest)
    start = time.monotonic()
    metrics = evaluate(manifest, ocr_fn=_ocr_from_path if use_engine else None)
    metrics["mean_latency_ms"] = int((time.monotonic() - start) * 1000 / max(1, len(manifest)))
    print(json.dumps(metrics, indent=2))
    if len(sys.argv) > 2:
        json.dump(metrics, open(sys.argv[2], "w"), indent=2)


if __name__ == "__main__":
    main()

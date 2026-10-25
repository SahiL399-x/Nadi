"""Run the real OCR pipeline over a directory of images and write predictions.

Runs INSIDE an ml-service container (needs paddleocr). CPU or GPU image both work.
Usage: python bench/run_ocr_dir.py <images_dir> <out_predictions.json>
Each prediction: {stem: {raw_ocr_text, fields:[{testNameRaw,testNameNormalized,
valueRaw,valueNumeric,unit,flag}]}}. Stem = filename without extension (the md5).
"""
import json
import sys
import time
from pathlib import Path

from app.ocr.engine import run_ocr
from app.ocr.normalize import normalize_fields
from app.ocr.parse import parse_fields
from app.ocr.preprocess import load_and_validate


def main() -> None:
    images_dir = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    paths = sorted(p for p in images_dir.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"})
    preds: dict = {}
    start = time.monotonic()
    for i, p in enumerate(paths, 1):
        try:
            img = load_and_validate(p.read_bytes())
            lines = run_ocr(img)
            raw_text = " ".join(ln["text"] for ln in lines)
            fields = normalize_fields(parse_fields(lines))["fields"]
            preds[p.stem] = {
                "raw_ocr_text": raw_text,
                "fields": [
                    {k: f[k] for k in ("testNameRaw", "testNameNormalized", "valueRaw", "valueNumeric", "unit", "flag")}
                    for f in fields
                ],
            }
        except Exception as exc:  # noqa: BLE001 — record the failure, keep going
            preds[p.stem] = {"raw_ocr_text": "", "fields": [], "error": type(exc).__name__}
        if i % 25 == 0:
            print(f"  {i}/{len(paths)} images, {time.monotonic()-start:.0f}s", flush=True)
    out_path.write_text(json.dumps(preds), encoding="utf-8")
    print(f"wrote {out_path}: {len(preds)} predictions in {time.monotonic()-start:.0f}s", flush=True)


if __name__ == "__main__":
    main()

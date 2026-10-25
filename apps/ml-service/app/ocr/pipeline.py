import time

from app.ocr import storage
from app.ocr.engine import MODEL_VERSION, run_ocr
from app.ocr.normalize import normalize_fields
from app.ocr.parse import parse_fields
from app.ocr.preprocess import load_and_validate


def to_labs(fields: list[dict]) -> list[dict]:
    # Back-compat LabValue list: only confidently-parsed, known analytes with a flag.
    labs = []
    for f in fields:
        if f["valueNumeric"] is None or "unknown_analyte" in f["qualityFlags"] or not f["flag"]:
            continue
        labs.append({
            "analyte": f["testNameNormalized"], "value": f["valueNumeric"],
            "unit": f["unit"], "refRange": f["referenceRangeRaw"], "flag": f["flag"],
        })
    return labs


def _safe_result(latency_ms: int) -> dict:
    return {"labs": [], "fields": [], "needsReview": True, "warnings": ["extraction_failed"],
            "modelVersion": MODEL_VERSION, "latencyMs": latency_ms}


def extract_report(object_key: str, *, ocr_fn=None) -> dict:
    ocr_fn = ocr_fn or run_ocr
    start = time.monotonic()
    try:
        image = load_and_validate(storage.fetch_object(object_key))
        lines = ocr_fn(image)
        norm = normalize_fields(parse_fields(lines))
        fields = norm["fields"]
        labs = to_labs(fields)
        needs_review = (
            not fields
            or any(f["qualityFlags"] for f in fields)
            or len(labs) < len(fields)
        )
        return {
            "labs": labs, "fields": fields, "needsReview": needs_review,
            "warnings": norm["warnings"], "modelVersion": MODEL_VERSION,
            "latencyMs": int((time.monotonic() - start) * 1000),
        }
    except Exception:  # noqa: BLE001 — never crash the consultation flow
        return _safe_result(int((time.monotonic() - start) * 1000))

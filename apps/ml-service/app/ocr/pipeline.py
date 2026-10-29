import logging
import time

from app.ocr import storage
from app.ocr.engine import MODEL_VERSION, run_ocr
from app.ocr.normalize import normalize_fields
from app.ocr.parse import parse_fields
from app.ocr.preprocess import load_document

logger = logging.getLogger(__name__)


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
        images = load_document(storage.fetch_object(object_key))
        fields: list[dict] = []
        warnings: list[str] = []
        for image in images:
            norm = normalize_fields(parse_fields(ocr_fn(image)))
            fields.extend(norm["fields"])
            warnings.extend(norm["warnings"])
        labs = to_labs(fields)
        needs_review = (
            not fields
            or any(f["qualityFlags"] for f in fields)
            or len(labs) < len(fields)
        )
        return {
            "labs": labs, "fields": fields, "needsReview": needs_review,
            "warnings": warnings, "modelVersion": MODEL_VERSION,
            "latencyMs": int((time.monotonic() - start) * 1000),
        }
    except Exception as exc:  # noqa: BLE001 — never crash the consultation flow
        latency_ms = int((time.monotonic() - start) * 1000)
        # Metadata only: exception type + latency. Never log the object key,
        # image bytes, or any extracted report content.
        logger.warning("ocr_extraction_failed exc_type=%s latency_ms=%d", type(exc).__name__, latency_ms)
        return _safe_result(latency_ms)

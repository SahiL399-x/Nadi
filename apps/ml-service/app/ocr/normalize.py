import json
import re
from pathlib import Path

_VOCAB_PATH = Path(__file__).resolve().parent / "data" / "analyte_vocab.json"

# Curated aliases take precedence over the data-derived vocab. (canonical, unit).
# Their units are hand-verified, so a unit mismatch against them is a real signal
# (unlike the noisy source units in the data vocab). Keep curated + reviewed.
_CURATED: dict[str, tuple[str, str]] = {
    "HAEMOGLOBIN": ("Haemoglobin", "g/dL"),
    "HEMOGLOBIN": ("Haemoglobin", "g/dL"),
    "HB": ("Haemoglobin", "g/dL"),
    "RBC COUNT": ("RBC Count", "mill/cu.mm"),
    "MCV": ("MCV", "fL"),
    "TSH": ("TSH", "uIU/mL"),
    "FREE T4": ("Free T4", "ng/dL"),
    "FASTING GLUCOSE": ("Fasting Glucose", "mg/dL"),
    "HBA1C": ("HbA1c", "%"),
}

_LOW_CONF = 0.60
_RANGE = re.compile(r"(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)")

_vocab_cache: dict | None = None


def _vocab() -> dict:
    """Lazy-load the NidaanKosha-derived analyte vocabulary (built offline by
    scripts/build_analyte_vocab.py). Missing file -> empty (curated-only)."""
    global _vocab_cache
    if _vocab_cache is None:
        try:
            _vocab_cache = json.loads(_VOCAB_PATH.read_text(encoding="utf-8"))
        except FileNotFoundError:
            _vocab_cache = {}
    return _vocab_cache


def _canon_key(name: str) -> str:
    # MUST stay byte-identical to scripts/build_analyte_vocab.canon_key so that
    # OCR names normalize to the same keys the vocabulary was built with.
    cleaned = re.sub(r"[^A-Z0-9()%/.\-+ ]", " ", str(name).upper())
    return re.sub(r"\s+", " ", cleaned).strip()


def compute_flag(value: float, ref_range: str) -> str:
    m = _RANGE.search(ref_range or "")
    if not m:
        return ""
    lo, hi = float(m.group(1)), float(m.group(2))
    if value < lo:
        return "L"
    if value > hi:
        return "H"
    return "N"


def _resolve(raw_name: str) -> tuple[str, str, str, bool]:
    """Return (canonical, expected_unit, loinc, unit_trusted) for an OCR name.
    Exact-normalized match only — never fuzzy-guess an analyte."""
    key = _canon_key(raw_name)
    curated = _CURATED.get(key)
    if curated:
        return curated[0], curated[1], "", True
    hit = _vocab().get(key)
    if hit:
        return hit["canonical"], hit.get("unit", ""), hit.get("loinc", ""), False
    return raw_name.strip(), "", "", False


def normalize_fields(raw: list[dict]) -> dict:
    fields: list[dict] = []
    warnings: list[str] = []
    for r in raw:
        quality: list[str] = []
        canonical, expected_unit, loinc, unit_trusted = _resolve(r["testNameRaw"])
        if not loinc and canonical == r["testNameRaw"].strip() and not unit_trusted:
            quality.append("unknown_analyte")

        try:
            value_numeric: float | None = float(r["valueRaw"])
        except (ValueError, TypeError):
            value_numeric = None
            quality.append("unparseable_value")

        unit = r.get("unitRaw", "")
        if unit_trusted and expected_unit and unit and unit.lower() != expected_unit.lower():
            quality.append("unit_mismatch")
            warnings.append(f"unit mismatch for {canonical}: got {unit}, expected {expected_unit}")

        if r.get("conf", 1.0) < _LOW_CONF:
            quality.append("low_confidence")

        flag = compute_flag(value_numeric, r["referenceRangeRaw"]) if value_numeric is not None else ""

        fields.append({
            "testNameRaw": r["testNameRaw"],
            "testNameNormalized": canonical,
            "valueRaw": r["valueRaw"],
            "valueNumeric": value_numeric,
            "unit": unit,
            "referenceRangeRaw": r.get("referenceRangeRaw", ""),
            "flag": flag,
            "loinc": loinc,
            "sourceRegion": r.get("sourceRegion", [0, 0, 0, 0]),
            "qualityFlags": quality,
        })
    return {"fields": fields, "warnings": warnings}

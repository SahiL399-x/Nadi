import re

# Seed alias dictionary: raw (upper, spaces collapsed) -> (canonical name, expected unit).
# Expand from NidaanKosha/LOINC names later; keep curated + reviewed, never inferred.
_ALIASES: dict[str, tuple[str, str]] = {
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


def _canon_key(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().upper())


def normalize_fields(raw: list[dict]) -> dict:
    fields: list[dict] = []
    warnings: list[str] = []
    for r in raw:
        quality: list[str] = []
        key = _canon_key(r["testNameRaw"])
        canonical, expected_unit = _ALIASES.get(key, (r["testNameRaw"].strip(), ""))
        if key not in _ALIASES:
            quality.append("unknown_analyte")

        try:
            value_numeric: float | None = float(r["valueRaw"])
        except (ValueError, TypeError):
            value_numeric = None
            quality.append("unparseable_value")

        unit = r.get("unitRaw", "")
        if expected_unit and unit and unit.lower() != expected_unit.lower():
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
            "sourceRegion": r.get("sourceRegion", [0, 0, 0, 0]),
            "qualityFlags": quality,
        })
    return {"fields": fields, "warnings": warnings}

from app.redflags import check

MODEL_VERSION = "stub-keyword-v0"


def _specialties(primary: str, alts: list[str]) -> list[dict]:
    names = [primary, *alts][:3]
    scores = [0.82, 0.11, 0.07][: len(names)]
    return [{"name": n, "score": s} for n, s in zip(names, scores, strict=False)]


def run(symptom_text: str, labs: list[dict], age: int | None, sex: str | None) -> dict:
    t = symptom_text.lower()
    red_flags = check(symptom_text)
    if red_flags or ("chest" in t and "breath" in t):
        return {
            "acuity": "EMERGENCY",
            "acuityConfidence": 0.97,
            "specialties": _specialties("Emergency Medicine", ["Cardiology", "General Medicine"]),
            "drivers": [{"feature": "red_flag_rule", "contribution": 1.0}],
            "labs": labs,
            "redFlags": red_flags or ["chest pain with breathlessness"],
            "modelVersion": MODEL_VERSION,
        }
    if any(k in t for k in ("chakkar", "dizzy", "weak", "weakness")):
        return {
            "acuity": "PRIORITY",
            "acuityConfidence": 0.74,
            "specialties": _specialties("General Medicine", ["Haematology", "Cardiology"]),
            "drivers": [
                {"feature": "dizziness", "contribution": 0.44},
                {"feature": "low_haemoglobin", "contribution": 0.31},
            ],
            "labs": labs,
            "redFlags": [],
            "modelVersion": MODEL_VERSION,
        }
    if any(k in t for k in ("fever", "cough", "cold", "bukhar", "khansi")):
        return {
            "acuity": "ROUTINE",
            "acuityConfidence": 0.81,
            "specialties": _specialties("General Physician", ["ENT", "General Medicine"]),
            "drivers": [{"feature": "fever", "contribution": 0.52}],
            "labs": labs,
            "redFlags": [],
            "modelVersion": MODEL_VERSION,
        }
    return {
        "acuity": "ROUTINE",
        "acuityConfidence": 0.6,
        "specialties": _specialties("General Physician", ["General Medicine", "ENT"]),
        "drivers": [{"feature": "unspecified_symptom", "contribution": 0.3}],
        "labs": labs,
        "redFlags": [],
        "modelVersion": MODEL_VERSION,
    }

from app.redflags import check

MODEL_VERSION = "stub-keyword-v0"


def _specialties(primary: str, alts: list[str]) -> list[dict]:
    names = [primary, *alts][:3]
    scores = [0.82, 0.11, 0.07][: len(names)]
    return [{"name": n, "score": s} for n, s in zip(names, scores, strict=False)]


def _result(
    acuity: str, conf: float, primary: str, alts: list[str], driver: str,
    labs: list[dict], red_flags: list[str] | None = None,
) -> dict:
    return {
        "acuity": acuity,
        "acuityConfidence": conf,
        "specialties": _specialties(primary, alts),
        "drivers": [{"feature": driver, "contribution": 0.6}],
        "labs": labs,
        "redFlags": red_flags or [],
        "modelVersion": MODEL_VERSION,
    }


# Ordered keyword rules (first match wins). Specialties are limited to those that
# have seeded doctors so "See doctors" always returns a list. English + common
# Hindi/Marathi terms. This is the deterministic Phase-1.5 stand-in for the
# trained triage model; it routes, it does not diagnose.
_RULES: list[tuple[tuple[str, ...], str, float, str, list[str], str]] = [
    # Chest pain on its own is treated cautiously (urgent) even without the
    # breathlessness red flag, and routed to Cardiology.
    (("chest", "seene", "heart"), "URGENT", 0.78, "Cardiology",
     ["General Medicine", "Emergency Medicine"], "chest_pain"),
    (("rash", "itch", "skin", "daane", "pimple", "acne", "khujli"), "ROUTINE", 0.80,
     "Dermatology", ["General Physician"], "skin_symptom"),
    (("ear", "nose", "throat", "gala", "sinus", "tonsil", "kaan", "naak"), "ROUTINE", 0.79,
     "ENT", ["General Physician"], "ent_symptom"),
    (("period", "pregnan", "menstru", "gynae", "vaginal", "garbh", "mahvari"), "PRIORITY", 0.76,
     "Gynaecology", ["General Medicine"], "womens_health"),
    (("child", "baby", "infant", "bachcha", "newborn", "toddler"), "PRIORITY", 0.77,
     "Paediatrics", ["General Physician"], "paediatric"),
    (("joint", "knee", "back", "bone", "fracture", "sprain", "ghutna", "kamar", "haddi"),
     "ROUTINE", 0.78, "Orthopaedics", ["General Medicine"], "musculoskeletal"),
    (("chakkar", "dizzy", "weak", "weakness", "anaemi", "anemia", "pale", "thakan"),
     "PRIORITY", 0.74, "General Medicine", ["Haematology", "Cardiology"], "dizziness_or_fatigue"),
    (("fever", "cough", "cold", "bukhar", "khansi", "sardi"), "ROUTINE", 0.81,
     "General Physician", ["ENT", "General Medicine"], "fever_or_cough"),
    (("headache", "migraine", "sar dard", "sir dard"), "ROUTINE", 0.72,
     "General Medicine", ["General Physician"], "headache"),
    (("stomach", "abdomen", "pet", "vomit", "nausea", "loose", "diarrh", "ulti", "dast"),
     "PRIORITY", 0.73, "General Medicine", ["General Physician"], "abdominal"),
]


def run(symptom_text: str, labs: list[dict], age: int | None, sex: str | None) -> dict:
    t = symptom_text.lower()
    red_flags = check(symptom_text)
    if red_flags or ("chest" in t and "breath" in t):
        return _result(
            "EMERGENCY", 0.97, "Emergency Medicine", ["Cardiology", "General Medicine"],
            "red_flag_rule", labs, red_flags or ["chest pain with breathlessness"],
        )
    for keywords, acuity, conf, primary, alts, driver in _RULES:
        if any(k in t for k in keywords):
            return _result(acuity, conf, primary, alts, driver, labs)
    return _result(
        "ROUTINE", 0.6, "General Physician", ["General Medicine", "ENT"],
        "unspecified_symptom", labs,
    )

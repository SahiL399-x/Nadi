MODEL_VERSION = "stub-keyword-v0"


def _specialties(primary: str, alts: list[str]) -> list[dict]:
    names = [primary, *alts][:3]
    scores = [0.82, 0.11, 0.07][: len(names)]
    return [{"name": n, "score": s} for n, s in zip(names, scores, strict=False)]


def _result(primary: str, alts: list[str], labs: list[dict]) -> dict:
    return {"specialties": _specialties(primary, alts), "labs": labs, "modelVersion": MODEL_VERSION}


# Ordered keyword rules (first match wins). Specialties limited to those with seeded
# doctors so "See doctors" always returns a list. English + common Hindi/Marathi terms.
# Deterministic stand-in for the trained model; it routes, it does not diagnose.
_RULES: list[tuple[tuple[str, ...], str, list[str]]] = [
    (("chest", "seene", "heart"), "Cardiology", ["General Medicine", "General Physician"]),
    (("rash", "itch", "skin", "daane", "pimple", "acne", "khujli"), "Dermatology", ["General Physician"]),
    (("ear", "nose", "throat", "gala", "sinus", "tonsil", "kaan", "naak"), "ENT", ["General Physician"]),
    (("period", "pregnan", "menstru", "gynae", "vaginal", "garbh", "mahvari"), "Gynaecology", ["General Medicine"]),
    (("child", "baby", "infant", "bachcha", "newborn", "toddler"), "Paediatrics", ["General Physician"]),
    (("joint", "knee", "back", "bone", "fracture", "sprain", "ghutna", "kamar", "haddi"), "Orthopaedics", ["General Medicine"]),
    (("chakkar", "dizzy", "weak", "weakness", "anaemi", "anemia", "pale", "thakan"), "General Medicine", ["Haematology", "Cardiology"]),
    (("fever", "cough", "cold", "bukhar", "khansi", "sardi"), "General Physician", ["ENT", "General Medicine"]),
    (("headache", "migraine", "sar dard", "sir dard"), "General Medicine", ["General Physician"]),
    (("stomach", "abdomen", "pet", "vomit", "nausea", "loose", "diarrh", "ulti", "dast"), "General Medicine", ["General Physician"]),
]


def run(symptom_text: str, labs: list[dict], age: int | None, sex: str | None) -> dict:
    t = symptom_text.lower()
    for keywords, primary, alts in _RULES:
        if any(k in t for k in keywords):
            return _result(primary, alts, labs)
    return _result("General Physician", ["General Medicine", "ENT"], labs)

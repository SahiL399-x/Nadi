_ANAEMIA = [
    {"analyte": "Haemoglobin", "value": 9.1, "unit": "g/dL", "refRange": "12.0 - 15.5", "flag": "L"},
    {"analyte": "RBC Count", "value": 3.8, "unit": "mill/cu.mm", "refRange": "4.2 - 5.4", "flag": "L"},
    {"analyte": "MCV", "value": 72.0, "unit": "fL", "refRange": "80 - 100", "flag": "L"},
]
_THYROID = [
    {"analyte": "TSH", "value": 7.8, "unit": "uIU/mL", "refRange": "0.4 - 4.0", "flag": "H"},
    {"analyte": "Free T4", "value": 0.7, "unit": "ng/dL", "refRange": "0.8 - 1.8", "flag": "L"},
]
_DIABETES = [
    {"analyte": "Fasting Glucose", "value": 148.0, "unit": "mg/dL", "refRange": "70 - 100", "flag": "H"},
    {"analyte": "HbA1c", "value": 7.9, "unit": "%", "refRange": "4.0 - 5.6", "flag": "H"},
]


def extract(object_key: str) -> list[dict]:
    k = object_key.lower()
    if "thyroid" in k:
        return _THYROID
    if "diabet" in k or "glucose" in k or "sugar" in k:
        return _DIABETES
    return _ANAEMIA

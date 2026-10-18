_LEXICON = {
    "chakkar": "dizziness", "dizzy": "dizziness",
    "jalan": "burning", "pet": "abdomen",
    "bukhar": "fever", "fever": "fever",
    "khansi": "cough", "cough": "cough",
    "sar": "head", "dard": "pain",
    "saans": "breathlessness", "breath": "breathlessness",
}


def normalise(text: str) -> dict:
    t = text.lower()
    entities = sorted({canon for token, canon in _LEXICON.items() if token in t})
    normalised = ", ".join(entities) if entities else t.strip()
    return {"entities": entities, "normalised": normalised}

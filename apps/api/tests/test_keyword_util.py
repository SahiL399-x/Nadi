from app.services.keyword_util import normalize_keywords


def test_lowercases_trims_dedupes_preserving_order():
    assert normalize_keywords([" Fever ", "COUGH", "fever", "cough"]) == ["fever", "cough"]


def test_drops_empties():
    assert normalize_keywords(["", "  ", "diabetes"]) == ["diabetes"]


def test_caps_at_limit():
    out = normalize_keywords([f"k{i}" for i in range(50)], cap=15)
    assert len(out) == 15
    assert out[0] == "k0"

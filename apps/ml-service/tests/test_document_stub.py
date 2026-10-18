from app.document_stub import extract


def test_anaemia_panel_returns_low_haemoglobin():
    labs = extract("anaemia/report1.webp")
    hb = next(x for x in labs if x["analyte"] == "Haemoglobin")
    assert hb["flag"] == "L"


def test_unknown_key_defaults_to_anaemia_panel():
    labs = extract("random.webp")
    assert any(x["analyte"] == "Haemoglobin" for x in labs)

from app import main
from app.config import settings


def test_flag_off_returns_stub_labs_only(client, monkeypatch):
    monkeypatch.setattr(settings, "ml_ocr_enabled", False)
    r = client.post("/ml/v1/document", json={"objectKey": "anaemia/r1.webp"})
    body = r.json()
    assert r.status_code == 200
    assert any(x["analyte"] == "Haemoglobin" for x in body["labs"])
    assert "fields" not in body  # off-path unchanged from today


def test_flag_on_returns_additive_fields(client, monkeypatch):
    monkeypatch.setattr(settings, "ml_ocr_enabled", True)
    fake = {"labs": [{"analyte": "Haemoglobin", "value": 9.1, "unit": "g/dL",
                      "refRange": "12.0 - 15.5", "flag": "L"}],
            "fields": [{"testNameNormalized": "Haemoglobin"}], "needsReview": False,
            "warnings": [], "modelVersion": "test", "latencyMs": 5}
    monkeypatch.setattr(main, "extract_report", lambda k: fake)
    r = client.post("/ml/v1/document", json={"objectKey": "x.webp"})
    body = r.json()
    assert body["fields"][0]["testNameNormalized"] == "Haemoglobin"
    assert body["needsReview"] is False
    assert body["modelVersion"] == "test"

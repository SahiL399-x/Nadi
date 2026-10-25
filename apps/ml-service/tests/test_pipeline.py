import pytest

from app.ocr import pipeline, storage


def _fake_ocr(_image):
    return [
        {"text": "Haemoglobin", "box": [10, 100, 80, 12], "conf": 0.98},
        {"text": "9.1", "box": [200, 101, 30, 12], "conf": 0.97},
        {"text": "g/dL", "box": [260, 100, 40, 12], "conf": 0.96},
        {"text": "12.0 - 15.5", "box": [340, 100, 80, 12], "conf": 0.95},
    ]


def _png(monkeypatch):
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (500, 200), (255, 255, 255)).save(buf, format="PNG")
    monkeypatch.setattr(storage, "fetch_object", lambda k: buf.getvalue())


def test_extract_report_returns_backcompat_labs_and_fields(monkeypatch):
    _png(monkeypatch)
    res = pipeline.extract_report("anaemia/r1.webp", ocr_fn=_fake_ocr)
    assert res["labs"] == [
        {"analyte": "Haemoglobin", "value": 9.1, "unit": "g/dL", "refRange": "12.0 - 15.5", "flag": "L"}
    ]
    assert res["fields"][0]["testNameNormalized"] == "Haemoglobin"
    assert res["modelVersion"]
    assert isinstance(res["latencyMs"], int)
    assert res["needsReview"] is False


def test_fetch_failure_returns_safe_review_result(monkeypatch):
    def _boom(_k):
        raise storage.StorageError("nope")
    monkeypatch.setattr(storage, "fetch_object", _boom)
    res = pipeline.extract_report("missing.webp", ocr_fn=_fake_ocr)
    assert res["labs"] == []
    assert res["fields"] == []
    assert res["needsReview"] is True


def test_unknown_or_unparseable_sets_needs_review(monkeypatch):
    _png(monkeypatch)

    def _ocr(_image):
        return [
            {"text": "Mystery Analyte", "box": [10, 50, 80, 12], "conf": 0.98},
            {"text": "5.0", "box": [200, 50, 30, 12], "conf": 0.98},
        ]
    res = pipeline.extract_report("x.webp", ocr_fn=_ocr)
    assert res["needsReview"] is True  # unknown_analyte triggers review
    assert res["labs"] == []           # unknown analytes excluded from back-compat labs

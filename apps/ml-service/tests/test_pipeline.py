import io
from unittest.mock import patch

import pytest
from PIL import Image

from app.ocr import pipeline, storage


def _pdf_bytes(pages: int = 2) -> bytes:
    imgs = [Image.new("RGB", (240, 320), "white") for _ in range(pages)]
    buf = io.BytesIO()
    imgs[0].save(buf, format="PDF", save_all=True, append_images=imgs[1:])
    return buf.getvalue()


def test_extract_report_concatenates_fields_across_pdf_pages(monkeypatch):
    monkeypatch.setattr(storage, "fetch_object", lambda key: _pdf_bytes(pages=2))

    # one OCR "line" per page -> a parseable row "Haemoglobin 9.1 g/dL 12.0 - 15.5"
    def fake_ocr(_image):
        return [
            {"text": "Haemoglobin", "box": [10, 100, 120, 30], "conf": 0.95},
            {"text": "9.1", "box": [200, 100, 40, 30], "conf": 0.95},
            {"text": "g/dL", "box": [260, 100, 50, 30], "conf": 0.95},
            {"text": "12.0 - 15.5", "box": [340, 100, 120, 30], "conf": 0.95},
        ]

    res = pipeline.extract_report("reports/upload/u/doc.pdf", ocr_fn=fake_ocr)
    # 2 pages -> 2 Haemoglobin fields
    assert len(res["fields"]) == 2
    assert all(f["testNameNormalized"] == "Haemoglobin" for f in res["fields"])


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


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (80, 80), "white").save(buf, format="PNG")
    return buf.getvalue()


def test_extract_report_enhances_only_upload_keys(monkeypatch):
    monkeypatch.setattr(storage, "fetch_object", lambda key: _png_bytes())
    calls = {"n": 0}

    def spy_enhance(img):
        calls["n"] += 1
        return img

    with patch.object(pipeline, "enhance", spy_enhance):
        pipeline.extract_report("reports/scan/u/a.webp", ocr_fn=lambda im: [])
        assert calls["n"] == 0  # scan source: no enhancement
        pipeline.extract_report("reports/upload/u/a.webp", ocr_fn=lambda im: [])
        assert calls["n"] == 1  # upload source: enhanced

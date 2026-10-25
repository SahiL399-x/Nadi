# NADI ML Workstream A — Lab-report OCR Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the filename-keyword `document_stub` with a real, benchmarked PaddleOCR lab-report extraction pipeline, behind a feature flag, with a strictly additive `document()` contract.

**Architecture:** A new `ocr/` package inside the existing `apps/ml-service` FastAPI container. The service fetches the report image from MinIO by key, runs PaddleOCR, groups boxes into rows, parses and normalizes lab fields, and returns the existing `labs` array plus additive structured `fields`. The real engine is isolated behind a thin adapter so all parsing/normalization logic is unit-testable with synthetic OCR output; the real model is exercised only by a standalone benchmark harness. A feature flag (`ML_OCR_ENABLED`, default off) keeps the running app on the stub until the benchmark passes.

**Tech Stack:** Python 3.11 (service container), FastAPI, PaddleOCR 3.x (PP-OCRv5 lightweight), Pillow, OpenCV (headless), boto3 (MinIO), pydantic-settings, pytest.

## Global Constraints

- **Additive contract only** — `document()` MUST keep returning `labs: [{analyte,value,unit,refRange,flag}]` byte-compatibly (consumed by `apps/api/app/services/consultation_service.py:49`). New fields are added, never substituted.
- **Feature-flagged** — real OCR runs only when `ML_OCR_ENABLED` is true; default false → identical to today's stub behavior.
- **Never crash the consultation flow** — any engine/file failure returns a safe `needsReview=true` empty result, never raises out of `document()`.
- **No fabricated results** — accuracy comes only from the benchmark harness output; never hardcode or claim a number.
- **Synthetic/de-identified data only**; **never log raw report content** (log metadata + correlation id only).
- **Keep the deterministic red-flag layer** (`redflags.py`) untouched.
- **Existing suites stay green** (ml-service pytest + api pytest) after every task.
- **Dependency versions pinned only after a smoke test** against the current official PaddleOCR install matrix (blueprint R1/R2). The real-engine adapter in `ocr/engine.py` is the single version-sensitive seam.
- **GPU used fully on the dev 3050 for the service/benchmark, but kept CPU-runnable** so the deferred production host stays open.
- **Spec:** `docs/superpowers/specs/2026-10-25-nadi-ml-workstream-a-ocr-design.md`.

### Shared type shapes (used across tasks — exact keys)

```python
# OcrLine: one recognized text line from the engine adapter
OcrLine = dict  # {"text": str, "box": [x, y, w, h], "conf": float}  (box ints, conf 0..1)

# RawField: one candidate lab row before normalization
RawField = dict  # {"testNameRaw": str, "valueRaw": str, "unitRaw": str,
                 #  "referenceRangeRaw": str, "sourceRegion": [x,y,w,h], "conf": float}

# Field: a normalized lab field (additive output)
Field = dict  # {"testNameRaw": str, "testNameNormalized": str, "valueRaw": str,
              #  "valueNumeric": float | None, "unit": str, "referenceRangeRaw": str,
              #  "flag": "L"|"N"|"H"|"", "sourceRegion": [x,y,w,h], "qualityFlags": list[str]}

# LabValue (back-compat): {"analyte": str, "value": float, "unit": str, "refRange": str, "flag": "L"|"N"|"H"}

# ExtractResult (document() when flag on):
# {"labs": list[LabValue], "fields": list[Field], "needsReview": bool,
#  "warnings": list[str], "modelVersion": str, "latencyMs": int}
```

---

### Task 1: ML-service settings + MinIO object fetch (`ocr/storage.py`)

**Files:**
- Modify: `apps/ml-service/pyproject.toml` (add runtime deps `boto3`, `pydantic-settings`)
- Create: `apps/ml-service/app/config.py`
- Create: `apps/ml-service/app/ocr/__init__.py` (empty)
- Create: `apps/ml-service/app/ocr/storage.py`
- Test: `apps/ml-service/tests/test_storage.py`

**Interfaces:**
- Produces: `settings` (with `.s3_endpoint/.s3_key/.s3_secret/.s3_bucket/.ml_ocr_enabled`); `fetch_object(object_key: str) -> bytes`; `StorageError(Exception)`.

- [ ] **Step 1: Add deps to `pyproject.toml`**

In `apps/ml-service/pyproject.toml`, change the `dependencies` line to:
```toml
dependencies = ["fastapi>=0.115", "uvicorn[standard]>=0.30", "pydantic>=2.7", "pydantic-settings>=2.3", "boto3>=1.34"]
```

- [ ] **Step 2: Create `app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # MinIO / S3 (mirrors apps/api defaults so the same creds work in dev).
    s3_endpoint: str = "http://localhost:9000"
    s3_key: str = "nadi"
    s3_secret: str = "nadi12345"
    s3_bucket: str = "nadi-reports"

    # Real OCR is off until the benchmark passes; off == today's stub behavior.
    ml_ocr_enabled: bool = False


settings = Settings()
```

- [ ] **Step 3: Write the failing test `tests/test_storage.py`**

```python
import io

import pytest

from app.ocr import storage


class _FakeBody:
    def __init__(self, data: bytes):
        self._b = io.BytesIO(data)

    def read(self) -> bytes:
        return self._b.read()


def test_fetch_object_returns_bytes(monkeypatch):
    class _FakeClient:
        def get_object(self, Bucket, Key):
            assert Key == "anaemia/r1.webp"
            return {"Body": _FakeBody(b"IMG")}

    monkeypatch.setattr(storage, "_client", lambda: _FakeClient())
    assert storage.fetch_object("anaemia/r1.webp") == b"IMG"


def test_fetch_object_missing_raises_storage_error(monkeypatch):
    class _FakeClient:
        def get_object(self, Bucket, Key):
            raise RuntimeError("NoSuchKey")

    monkeypatch.setattr(storage, "_client", lambda: _FakeClient())
    with pytest.raises(storage.StorageError):
        storage.fetch_object("missing.webp")
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd apps/ml-service && python -m pytest tests/test_storage.py -v`
Expected: FAIL (`ModuleNotFoundError: app.ocr.storage`).

- [ ] **Step 5: Create `app/ocr/__init__.py` (empty) and `app/ocr/storage.py`**

```python
from functools import lru_cache

import boto3
from botocore.client import Config

from app.config import settings


class StorageError(Exception):
    """Raised when an object cannot be fetched."""


@lru_cache(maxsize=1)
def _client():
    return boto3.client(
        "s3", endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_key, aws_secret_access_key=settings.s3_secret,
        config=Config(signature_version="s3v4"), region_name="us-east-1",
    )


def fetch_object(object_key: str) -> bytes:
    try:
        obj = _client().get_object(Bucket=settings.s3_bucket, Key=object_key)
        return obj["Body"].read()
    except Exception as exc:  # noqa: BLE001 — surface a typed error, never leak key/content
        raise StorageError(f"could not fetch object (len={len(object_key)})") from exc
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd apps/ml-service && python -m pytest tests/test_storage.py -v`
Expected: PASS (2 passed). If `boto3`/`pydantic-settings` are missing locally, run `pip install -e ".[dev]" boto3 pydantic-settings` in the ml-service venv first.

- [ ] **Step 7: Commit**

```bash
git add apps/ml-service/pyproject.toml apps/ml-service/app/config.py apps/ml-service/app/ocr/__init__.py apps/ml-service/app/ocr/storage.py apps/ml-service/tests/test_storage.py
git commit -m "add ml-service settings and MinIO object fetch for OCR"
```

---

### Task 2: Image validation + load (`ocr/preprocess.py`)

**Files:**
- Modify: `apps/ml-service/pyproject.toml` (add `pillow`)
- Create: `apps/ml-service/app/ocr/preprocess.py`
- Test: `apps/ml-service/tests/test_preprocess.py`

**Interfaces:**
- Consumes: nothing from prior tasks.
- Produces: `load_and_validate(data: bytes, *, max_bytes: int = 15_000_000) -> PIL.Image.Image`; `InvalidImageError(Exception)`.

- [ ] **Step 1: Add `pillow` to `pyproject.toml` dependencies**

Append `"pillow>=10.3"` to the `dependencies` list in `apps/ml-service/pyproject.toml`.

- [ ] **Step 2: Write the failing test `tests/test_preprocess.py`**

```python
import io

import pytest
from PIL import Image

from app.ocr.preprocess import InvalidImageError, load_and_validate


def _png_bytes(size=(40, 20)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (255, 255, 255)).save(buf, format="PNG")
    return buf.getvalue()


def test_valid_png_loads_as_image():
    img = load_and_validate(_png_bytes())
    assert img.width == 40 and img.height == 20


def test_empty_bytes_rejected():
    with pytest.raises(InvalidImageError):
        load_and_validate(b"")


def test_non_image_bytes_rejected():
    with pytest.raises(InvalidImageError):
        load_and_validate(b"this is not an image")


def test_oversize_rejected():
    with pytest.raises(InvalidImageError):
        load_and_validate(_png_bytes(), max_bytes=10)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd apps/ml-service && python -m pytest tests/test_preprocess.py -v`
Expected: FAIL (`ModuleNotFoundError: app.ocr.preprocess`).

- [ ] **Step 4: Implement `app/ocr/preprocess.py`**

```python
import io

from PIL import Image, ImageOps, UnidentifiedImageError


class InvalidImageError(Exception):
    """Raised for empty, oversized, corrupt, or unsupported image data."""


def load_and_validate(data: bytes, *, max_bytes: int = 15_000_000) -> Image.Image:
    if not data:
        raise InvalidImageError("empty file")
    if len(data) > max_bytes:
        raise InvalidImageError("file too large")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidImageError("unsupported or corrupt image") from exc
    # Respect EXIF orientation, then normalize to RGB. Conservative: no deskew/
    # contrast changes here — the original is preserved upstream for review.
    img = ImageOps.exif_transpose(img).convert("RGB")
    return img
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd apps/ml-service && python -m pytest tests/test_preprocess.py -v`
Expected: PASS (4 passed).

- [ ] **Step 6: Commit**

```bash
git add apps/ml-service/pyproject.toml apps/ml-service/app/ocr/preprocess.py apps/ml-service/tests/test_preprocess.py
git commit -m "add OCR image validation and loading"
```

---

### Task 3: Row grouping + field parsing (`ocr/parse.py`)

**Files:**
- Create: `apps/ml-service/app/ocr/parse.py`
- Test: `apps/ml-service/tests/test_parse.py`

**Interfaces:**
- Consumes: `OcrLine` shape (see Shared types).
- Produces: `parse_fields(lines: list[dict]) -> list[dict]` returning `RawField`s. Row grouping by vertical overlap; within a row the leftmost text is the test name, the first numeric token is the value, a `lo - hi` pattern is the reference range, and a trailing non-numeric token after the value is the unit.

- [ ] **Step 1: Write the failing test `tests/test_parse.py`**

```python
from app.ocr.parse import parse_fields


def _line(text, x, y, w=60, h=12, conf=0.95):
    return {"text": text, "box": [x, y, w, h], "conf": conf}


def test_single_row_parses_name_value_unit_and_range():
    lines = [
        _line("Haemoglobin", 10, 100),
        _line("9.1", 200, 102),
        _line("g/dL", 260, 101),
        _line("12.0 - 15.5", 340, 100),
    ]
    fields = parse_fields(lines)
    assert len(fields) == 1
    f = fields[0]
    assert f["testNameRaw"] == "Haemoglobin"
    assert f["valueRaw"] == "9.1"
    assert f["unitRaw"] == "g/dL"
    assert f["referenceRangeRaw"] == "12.0 - 15.5"
    assert f["sourceRegion"][1] == 100


def test_two_rows_separated_by_y():
    lines = [
        _line("TSH", 10, 50), _line("7.8", 200, 51), _line("uIU/mL", 260, 50),
        _line("Free T4", 10, 200), _line("0.7", 200, 201), _line("ng/dL", 260, 200),
    ]
    fields = parse_fields(lines)
    assert [f["testNameRaw"] for f in fields] == ["TSH", "Free T4"]


def test_row_without_numeric_value_is_skipped():
    lines = [_line("Patient Name", 10, 10), _line("Ramesh Kumar", 200, 10)]
    assert parse_fields(lines) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/ml-service && python -m pytest tests/test_parse.py -v`
Expected: FAIL (`ModuleNotFoundError: app.ocr.parse`).

- [ ] **Step 3: Implement `app/ocr/parse.py`**

```python
import re

_NUM = re.compile(r"^[<>]?\d+(?:\.\d+)?$")
_RANGE = re.compile(r"\d+(?:\.\d+)?\s*[-–]\s*\d+(?:\.\d+)?")


def _row_key(box: list[int]) -> int:
    # Group by vertical band: midpoint bucketed to tolerate small y jitter.
    return (box[1] + box[3] // 2) // 14


def _bbox(boxes: list[list[int]]) -> list[int]:
    x0 = min(b[0] for b in boxes)
    y0 = min(b[1] for b in boxes)
    x1 = max(b[0] + b[2] for b in boxes)
    y1 = max(b[1] + b[3] for b in boxes)
    return [x0, y0, x1 - x0, y1 - y0]


def parse_fields(lines: list[dict]) -> list[dict]:
    rows: dict[int, list[dict]] = {}
    for ln in lines:
        rows.setdefault(_row_key(ln["box"]), []).append(ln)

    out: list[dict] = []
    for key in sorted(rows):
        cells = sorted(rows[key], key=lambda c: c["box"][0])
        texts = [c["text"].strip() for c in cells]

        value_idx = next((i for i, t in enumerate(texts) if _NUM.match(t)), None)
        if value_idx is None or value_idx == 0:
            continue  # no numeric value, or nothing to the left to name it

        name = " ".join(texts[:value_idx]).strip()
        value_raw = texts[value_idx].lstrip("<>")
        rest = texts[value_idx + 1 :]
        rng_match = next((m.group(0) for t in rest if (m := _RANGE.search(t))), "")
        unit = next((t for t in rest if not _RANGE.search(t) and not _NUM.match(t)), "")

        out.append({
            "testNameRaw": name,
            "valueRaw": value_raw,
            "unitRaw": unit,
            "referenceRangeRaw": rng_match,
            "sourceRegion": _bbox([c["box"] for c in cells]),
            "conf": min(c["conf"] for c in cells),
        })
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/ml-service && python -m pytest tests/test_parse.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add apps/ml-service/app/ocr/parse.py apps/ml-service/tests/test_parse.py
git commit -m "add OCR row grouping and lab-field parsing"
```

---

### Task 4: Normalization, unit check, and flag computation (`ocr/normalize.py`)

**Files:**
- Create: `apps/ml-service/app/ocr/normalize.py`
- Test: `apps/ml-service/tests/test_normalize.py`

**Interfaces:**
- Consumes: `RawField` list from `parse_fields`.
- Produces: `normalize_fields(raw: list[dict]) -> dict` → `{"fields": list[Field], "warnings": list[str]}`; `compute_flag(value: float, ref_range: str) -> str`.

- [ ] **Step 1: Write the failing test `tests/test_normalize.py`**

```python
from app.ocr.normalize import compute_flag, normalize_fields


def _raw(name, value, unit="", rng="", conf=0.95):
    return {"testNameRaw": name, "valueRaw": value, "unitRaw": unit,
            "referenceRangeRaw": rng, "sourceRegion": [0, 0, 1, 1], "conf": conf}


def test_compute_flag_low_normal_high():
    assert compute_flag(9.1, "12.0 - 15.5") == "L"
    assert compute_flag(13.0, "12.0 - 15.5") == "N"
    assert compute_flag(18.0, "12.0 - 15.5") == "H"
    assert compute_flag(9.1, "garbage") == ""


def test_known_analyte_normalized_and_flagged():
    res = normalize_fields([_raw("HAEMOGLOBIN", "9.1", "g/dL", "12.0 - 15.5")])
    f = res["fields"][0]
    assert f["testNameNormalized"] == "Haemoglobin"
    assert f["valueNumeric"] == 9.1
    assert f["flag"] == "L"
    assert "low_confidence" not in f["qualityFlags"]


def test_unparseable_value_flags_review_and_does_not_guess():
    res = normalize_fields([_raw("TSH", "abc", "uIU/mL", "0.4 - 4.0")])
    f = res["fields"][0]
    assert f["valueNumeric"] is None
    assert f["flag"] == ""
    assert "unparseable_value" in f["qualityFlags"]


def test_unit_mismatch_warns():
    res = normalize_fields([_raw("Haemoglobin", "9.1", "mg/dL", "12.0 - 15.5")])
    assert any("unit" in w for w in res["warnings"])
    assert "unit_mismatch" in res["fields"][0]["qualityFlags"]


def test_low_confidence_marks_quality_flag():
    res = normalize_fields([_raw("Haemoglobin", "9.1", "g/dL", "12.0 - 15.5", conf=0.40)])
    assert "low_confidence" in res["fields"][0]["qualityFlags"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/ml-service && python -m pytest tests/test_normalize.py -v`
Expected: FAIL (`ModuleNotFoundError: app.ocr.normalize`).

- [ ] **Step 3: Implement `app/ocr/normalize.py`**

```python
import re

# Seed alias dictionary: raw (upper, spaces collapsed) -> (canonical name, expected unit).
# Expand from NidaanKosha/LOINC names later; keep curated + reviewed, never inferred.
_ALIASES: dict[str, tuple[str, str]] = {
    "HAEMOGLOBIN": ("Haemoglobin", "g/dL"),
    "HEMOGLOBIN": ("Haemoglobin", "g/dL"),
    "HB": ("Haemoglobin", "g/dL"),
    "RBC COUNT": ("RBC Count", "mill/cu.mm"),
    "MCV": ("MCV", "fL"),
    "TSH": ("TSH", "uIU/mL"),
    "FREE T4": ("Free T4", "ng/dL"),
    "FASTING GLUCOSE": ("Fasting Glucose", "mg/dL"),
    "HBA1C": ("HbA1c", "%"),
}

_LOW_CONF = 0.60
_RANGE = re.compile(r"(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)")


def compute_flag(value: float, ref_range: str) -> str:
    m = _RANGE.search(ref_range or "")
    if not m:
        return ""
    lo, hi = float(m.group(1)), float(m.group(2))
    if value < lo:
        return "L"
    if value > hi:
        return "H"
    return "N"


def _canon_key(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().upper())


def normalize_fields(raw: list[dict]) -> dict:
    fields: list[dict] = []
    warnings: list[str] = []
    for r in raw:
        quality: list[str] = []
        key = _canon_key(r["testNameRaw"])
        canonical, expected_unit = _ALIASES.get(key, (r["testNameRaw"].strip(), ""))
        if key not in _ALIASES:
            quality.append("unknown_analyte")

        try:
            value_numeric: float | None = float(r["valueRaw"])
        except (ValueError, TypeError):
            value_numeric = None
            quality.append("unparseable_value")

        unit = r.get("unitRaw", "")
        if expected_unit and unit and unit.lower() != expected_unit.lower():
            quality.append("unit_mismatch")
            warnings.append(f"unit mismatch for {canonical}: got {unit}, expected {expected_unit}")

        if r.get("conf", 1.0) < _LOW_CONF:
            quality.append("low_confidence")

        flag = compute_flag(value_numeric, r["referenceRangeRaw"]) if value_numeric is not None else ""

        fields.append({
            "testNameRaw": r["testNameRaw"],
            "testNameNormalized": canonical,
            "valueRaw": r["valueRaw"],
            "valueNumeric": value_numeric,
            "unit": unit,
            "referenceRangeRaw": r.get("referenceRangeRaw", ""),
            "flag": flag,
            "sourceRegion": r.get("sourceRegion", [0, 0, 0, 0]),
            "qualityFlags": quality,
        })
    return {"fields": fields, "warnings": warnings}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/ml-service && python -m pytest tests/test_normalize.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add apps/ml-service/app/ocr/normalize.py apps/ml-service/tests/test_normalize.py
git commit -m "add OCR lab-field normalization, unit check, and flag computation"
```

---

### Task 5: Engine adapter + pipeline orchestration (`ocr/engine.py`, `ocr/pipeline.py`)

**Files:**
- Modify: `apps/ml-service/pyproject.toml` (add `opencv-python-headless`, `numpy`; `paddleocr` + `paddlepaddle` added/pinned in Task 7)
- Create: `apps/ml-service/app/ocr/engine.py`
- Create: `apps/ml-service/app/ocr/pipeline.py`
- Test: `apps/ml-service/tests/test_pipeline.py`

**Interfaces:**
- Consumes: `fetch_object`, `load_and_validate`, `parse_fields`, `normalize_fields`.
- Produces: `extract_report(object_key: str, *, ocr_fn=None) -> dict` returning an `ExtractResult`; `run_ocr(image) -> list[dict]` (OcrLines); `MODEL_VERSION: str`; `to_labs(fields: list[dict]) -> list[dict]`.
- Note: `run_ocr` wraps PaddleOCR and is the one version-sensitive seam. It is NOT unit-tested (real model too heavy); the pipeline is tested with an injected fake `ocr_fn`.

- [ ] **Step 1: Add `opencv-python-headless` and `numpy` to `pyproject.toml` dependencies**

Append `"opencv-python-headless>=4.9"` and `"numpy>=1.26"` to the `dependencies` list.

- [ ] **Step 2: Write the failing test `tests/test_pipeline.py`**

```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd apps/ml-service && python -m pytest tests/test_pipeline.py -v`
Expected: FAIL (`ModuleNotFoundError: app.ocr.pipeline`).

- [ ] **Step 4: Implement `app/ocr/engine.py`**

```python
from functools import lru_cache

# PP-OCRv5 lightweight (mobile) detection+recognition. GPU on the dev 3050,
# CPU-runnable for the deferred production host.
MODEL_VERSION = "paddleocr-ppocrv5-mobile"


@lru_cache(maxsize=1)
def _engine():
    # Imported lazily so unit tests (which inject a fake ocr_fn) never load Paddle.
    from paddleocr import PaddleOCR
    return PaddleOCR(use_angle_cls=True, lang="en", show_log=False)


def run_ocr(image) -> list[dict]:
    """Adapter: PaddleOCR result -> list[OcrLine]. This is the single
    version-sensitive seam — confirm the call signature and result shape against
    the installed PaddleOCR version during the Task 7 smoke test and adjust here.
    Everything downstream consumes the OcrLine shape and is version-independent."""
    import numpy as np
    result = _engine().ocr(np.array(image), cls=True)
    lines: list[dict] = []
    for page in result or []:
        for entry in page or []:
            box, (text, conf) = entry[0], entry[1]
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            lines.append({
                "text": text,
                "box": [int(min(xs)), int(min(ys)), int(max(xs) - min(xs)), int(max(ys) - min(ys))],
                "conf": float(conf),
            })
    return lines
```

- [ ] **Step 5: Implement `app/ocr/pipeline.py`**

```python
import time

from app.ocr import storage
from app.ocr.engine import MODEL_VERSION, run_ocr
from app.ocr.normalize import normalize_fields
from app.ocr.parse import parse_fields
from app.ocr.preprocess import load_and_validate


def to_labs(fields: list[dict]) -> list[dict]:
    # Back-compat LabValue list: only confidently-parsed, known analytes with a flag.
    labs = []
    for f in fields:
        if f["valueNumeric"] is None or "unknown_analyte" in f["qualityFlags"] or not f["flag"]:
            continue
        labs.append({
            "analyte": f["testNameNormalized"], "value": f["valueNumeric"],
            "unit": f["unit"], "refRange": f["referenceRangeRaw"], "flag": f["flag"],
        })
    return labs


def _safe_result(latency_ms: int) -> dict:
    return {"labs": [], "fields": [], "needsReview": True, "warnings": ["extraction_failed"],
            "modelVersion": MODEL_VERSION, "latencyMs": latency_ms}


def extract_report(object_key: str, *, ocr_fn=None) -> dict:
    ocr_fn = ocr_fn or run_ocr
    start = time.monotonic()
    try:
        image = load_and_validate(storage.fetch_object(object_key))
        lines = ocr_fn(image)
        norm = normalize_fields(parse_fields(lines))
        fields = norm["fields"]
        labs = to_labs(fields)
        needs_review = (
            not fields
            or any(f["qualityFlags"] for f in fields)
            or len(labs) < len(fields)
        )
        return {
            "labs": labs, "fields": fields, "needsReview": needs_review,
            "warnings": norm["warnings"], "modelVersion": MODEL_VERSION,
            "latencyMs": int((time.monotonic() - start) * 1000),
        }
    except Exception:  # noqa: BLE001 — never crash the consultation flow
        return _safe_result(int((time.monotonic() - start) * 1000))
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd apps/ml-service && python -m pytest tests/test_pipeline.py -v`
Expected: PASS (3 passed).

- [ ] **Step 7: Commit**

```bash
git add apps/ml-service/pyproject.toml apps/ml-service/app/ocr/engine.py apps/ml-service/app/ocr/pipeline.py apps/ml-service/tests/test_pipeline.py
git commit -m "add OCR engine adapter and extraction pipeline with safe fallback"
```

---

### Task 6: Wire `document()` behind the feature flag (additive contract)

**Files:**
- Modify: `apps/ml-service/app/main.py`
- Test: `apps/ml-service/tests/test_document_endpoint.py`

**Interfaces:**
- Consumes: `settings.ml_ocr_enabled`, `extract_report`, existing `document_stub.extract`.
- Produces: the additive `document()` HTTP contract.

- [ ] **Step 1: Write the failing test `tests/test_document_endpoint.py`**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/ml-service && python -m pytest tests/test_document_endpoint.py -v`
Expected: FAIL (`AttributeError: module 'app.main' has no attribute 'extract_report'`).

- [ ] **Step 3: Modify `app/main.py`**

Add imports near the top:
```python
from app.config import settings
from app.ocr.pipeline import extract_report
```

Replace the existing `document` endpoint with:
```python
@app.post("/ml/v1/document")
def document(req: DocumentRequest) -> dict:
    if settings.ml_ocr_enabled:
        return extract_report(req.objectKey)
    # Flag off: unchanged stub behavior (keeps the running app on the known path).
    return {"labs": extract(req.objectKey)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/ml-service && python -m pytest tests/test_document_endpoint.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Run the full ml-service suite (regression)**

Run: `cd apps/ml-service && python -m pytest -q`
Expected: all pass (new + existing `test_document_stub`, `test_triage_stub`, `test_symptom_stub`, `test_redflags`).

- [ ] **Step 6: Commit**

```bash
git add apps/ml-service/app/main.py apps/ml-service/tests/test_document_endpoint.py
git commit -m "serve real OCR from document() behind ML_OCR_ENABLED flag"
```

---

### Task 7: Dependencies, Dockerfile, and compose wiring (container build)

**Files:**
- Modify: `apps/ml-service/pyproject.toml` (add `paddleocr`, `paddlepaddle`; pin after smoke)
- Modify: `apps/ml-service/Dockerfile`
- Modify: `infra/docker-compose.yml` (ml-service env)

**Interfaces:** none (packaging). Verification deliverable = the ml-service container builds and `/ml/v1/health` passes with `ML_OCR_ENABLED=false`, and a one-shot in-container import of `paddleocr` succeeds.

- [ ] **Step 1: Verify current PaddleOCR install command**

Open https://github.com/PaddlePaddle/PaddleOCR (blueprint R1) and confirm the current pip install for PaddleOCR 3.x + the CPU `paddlepaddle` wheel compatible with Python 3.11. Record the exact versions in `docs/ml/MODEL_CARDS.md` (created in Task 8).

- [ ] **Step 2: Add OCR deps to `pyproject.toml`**

Append to `dependencies` (replace the version with the one verified in Step 1):
```toml
"paddleocr>=3.0",
"paddlepaddle>=3.0",
```
(The container uses the CPU wheel. GPU on the dev laptop is a separate host venv — see Task 8 bench README. Keep the container CPU-only so the deferred prod host stays open.)

- [ ] **Step 3: Update `apps/ml-service/Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /srv
# System libs required by OpenCV / PaddleOCR.
RUN apt-get update && apt-get install -y --no-install-recommends \
      libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .
COPY app ./app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

- [ ] **Step 4: Add ml-service env in `infra/docker-compose.yml`**

Under the `ml-service:` service, add an `environment:` block:
```yaml
    environment:
      S3_ENDPOINT: ${S3_ENDPOINT:-http://minio:9000}
      S3_KEY: nadi
      S3_SECRET: nadi12345
      S3_BUCKET: nadi-reports
      ML_OCR_ENABLED: ${ML_OCR_ENABLED:-false}
```

- [ ] **Step 5: Build and smoke-test the container**

Run:
```bash
docker compose -f infra/docker-compose.yml build ml-service
docker compose -f infra/docker-compose.yml up -d ml-service
docker compose -f infra/docker-compose.yml exec ml-service python -c "import paddleocr; print('paddleocr ok')"
```
Expected: build succeeds; `paddleocr ok` prints; `docker compose ... ps` shows ml-service healthy (health endpoint still 200 with flag off). This step needs network + time (large image); if the build is blocked (no network/disk), record the exact blocker per the blueprint's "blocked tests listed with reasons."

- [ ] **Step 6: Commit**

```bash
git add apps/ml-service/pyproject.toml apps/ml-service/Dockerfile infra/docker-compose.yml
git commit -m "package PaddleOCR in ml-service container and wire MinIO/flag env"
```

---

### Task 8: Benchmark harness + dataset/model-card docs

**Files:**
- Create: `apps/ml-service/bench/ocr_eval.py`
- Create: `apps/ml-service/bench/README.md`
- Create: `apps/ml-service/bench/fixtures/manifest.json` + one synthetic sample image
- Create: `docs/ml/DATASET_REGISTER.md`
- Create: `docs/ml/MODEL_CARDS.md`
- Test: `apps/ml-service/tests/test_ocr_eval.py`

**Interfaces:**
- Consumes: `extract_report` (with a fake `ocr_fn` in the test; the real engine in manual runs).
- Produces: `evaluate(manifest: list[dict], ocr_fn=None) -> dict` → metrics `{"n", "field_exact_match", "numeric_accuracy", "unit_accuracy", "pairing_accuracy", "cer", "mean_latency_ms"}`; `cer(pred: str, truth: str) -> float`.

- [ ] **Step 1: Write the failing test `tests/test_ocr_eval.py`**

```python
from app.bench_eval import cer, evaluate  # thin import shim; see Step 3


def test_cer_basic():
    assert cer("abc", "abc") == 0.0
    assert cer("abc", "abd") > 0.0


def test_evaluate_computes_field_metrics():
    manifest = [{
        "lines": [
            {"text": "Haemoglobin", "box": [10, 100, 80, 12], "conf": 0.98},
            {"text": "9.1", "box": [200, 100, 30, 12], "conf": 0.98},
            {"text": "g/dL", "box": [260, 100, 40, 12], "conf": 0.98},
            {"text": "12.0 - 15.5", "box": [340, 100, 80, 12], "conf": 0.98},
        ],
        "truth": [{"analyte": "Haemoglobin", "value": 9.1, "unit": "g/dL", "flag": "L"}],
    }]
    metrics = evaluate(manifest)
    assert metrics["n"] == 1
    assert metrics["numeric_accuracy"] == 1.0
    assert metrics["unit_accuracy"] == 1.0
    assert 0.0 <= metrics["cer"] <= 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/ml-service && python -m pytest tests/test_ocr_eval.py -v`
Expected: FAIL (`ModuleNotFoundError: app.bench_eval`).

- [ ] **Step 3: Implement the evaluator**

Create `apps/ml-service/app/bench_eval.py` (importable + unit-tested; the CLI wrapper lives in `bench/ocr_eval.py`):
```python
from app.ocr.normalize import normalize_fields
from app.ocr.parse import parse_fields


def cer(pred: str, truth: str) -> float:
    # Levenshtein distance / len(truth), clamped to [0, 1].
    if not truth:
        return 0.0 if not pred else 1.0
    m, n = len(truth), len(pred)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, n + 1):
            cur = dp[j]
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + (truth[i - 1] != pred[j - 1]))
            prev = cur
    return min(1.0, dp[n] / m)


def evaluate(manifest: list[dict], ocr_fn=None) -> dict:
    # Each manifest item provides pre-computed OCR `lines` (fixtures/tests) OR,
    # in a real run, the CLI supplies ocr_fn to produce lines from an image.
    n = num_ok = unit_ok = pair_ok = 0
    cers: list[float] = []
    for item in manifest:
        lines = item["lines"] if ocr_fn is None else ocr_fn(item["image_path"])
        fields = normalize_fields(parse_fields(lines))["fields"]
        by_name = {f["testNameNormalized"]: f for f in fields}
        for truth in item["truth"]:
            n += 1
            got = by_name.get(truth["analyte"])
            if got and got["valueNumeric"] == truth["value"]:
                num_ok += 1
            if got and got["unit"].lower() == truth["unit"].lower():
                unit_ok += 1
            if got and got["valueNumeric"] == truth["value"] and got["flag"] == truth["flag"]:
                pair_ok += 1
            cers.append(cer(got["testNameNormalized"] if got else "", truth["analyte"]))
    return {
        "n": n,
        "numeric_accuracy": (num_ok / n) if n else 0.0,
        "unit_accuracy": (unit_ok / n) if n else 0.0,
        "pairing_accuracy": (pair_ok / n) if n else 0.0,
        "field_exact_match": (pair_ok / n) if n else 0.0,
        "cer": (sum(cers) / len(cers)) if cers else 0.0,
        "mean_latency_ms": 0,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/ml-service && python -m pytest tests/test_ocr_eval.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Create the CLI wrapper `bench/ocr_eval.py`**

```python
"""Run OCR extraction over a manifest and print/save metrics.
Usage: python bench/ocr_eval.py <manifest.json> [out.json]
Manifest entries: {"image_path": "...", "truth": [{analyte,value,unit,flag}]}.
Real runs use the PaddleOCR engine; fixtures may inline pre-computed `lines`."""
import json
import sys
import time

from app.bench_eval import evaluate
from app.ocr.engine import run_ocr
from app.ocr.preprocess import load_and_validate
from app.ocr.storage import fetch_object  # noqa: F401 (available for key-based manifests)


def _ocr_from_path(path: str):
    with open(path, "rb") as fh:
        return run_ocr(load_and_validate(fh.read()))


def main() -> None:
    manifest = json.load(open(sys.argv[1]))
    use_engine = all("lines" not in item for item in manifest)
    start = time.monotonic()
    metrics = evaluate(manifest, ocr_fn=_ocr_from_path if use_engine else None)
    metrics["mean_latency_ms"] = int((time.monotonic() - start) * 1000 / max(1, len(manifest)))
    print(json.dumps(metrics, indent=2))
    if len(sys.argv) > 2:
        json.dump(metrics, open(sys.argv[2], "w"), indent=2)


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Create `bench/fixtures/manifest.json`**

```json
[
  {
    "lines": [
      {"text": "Haemoglobin", "box": [10, 100, 80, 12], "conf": 0.98},
      {"text": "9.1", "box": [200, 100, 30, 12], "conf": 0.98},
      {"text": "g/dL", "box": [260, 100, 40, 12], "conf": 0.98},
      {"text": "12.0 - 15.5", "box": [340, 100, 80, 12], "conf": 0.98}
    ],
    "truth": [{"analyte": "Haemoglobin", "value": 9.1, "unit": "g/dL", "flag": "L"}]
  }
]
```

- [ ] **Step 7: Verify the CLI runs on the fixture**

Run: `cd apps/ml-service && python bench/ocr_eval.py bench/fixtures/manifest.json`
Expected: prints JSON with `"numeric_accuracy": 1.0`, `"unit_accuracy": 1.0`.

- [ ] **Step 8: Write `bench/README.md`, `docs/ml/DATASET_REGISTER.md`, `docs/ml/MODEL_CARDS.md`**

`bench/README.md` contents:
```markdown
# OCR benchmark

## Fixture run (no dataset, no GPU)
    python bench/ocr_eval.py bench/fixtures/manifest.json

## Full Eka Care benchmark (288 images)
The Eka Care Medical Records Parsing Validation Set is test-only and may be gated.
1. On your machine: `huggingface-cli login` (read token; never commit it).
2. Download the dataset per its HF card into `bench/data/eka/` (DO NOT COMMIT the data).
3. Build a manifest mapping each image_path to its ground-truth fields.
4. GPU run on the dev 3050: create a Python 3.11/3.12 venv and install the GPU
   PaddlePaddle wheel per the official install matrix, then:
       python bench/ocr_eval.py bench/data/eka/manifest.json results/eka.json
5. Record the metrics in docs/ml/MODEL_CARDS.md. NEVER fine-tune on this test set.
```

`docs/ml/DATASET_REGISTER.md` — table with columns: name, URL, access date, license, gated?, modalities, split, allowed use. Seed rows for the Eka Care Validation Set (CC-BY-SA-4.0, test-only, benchmark-only), NidaanKosha (CC-BY-SA-4.0, structured, normalization only), Eka-IndicMTEB (CC-BY-SA-4.0, concept benchmark). Mark all three **benchmark-only, do not redistribute derived data**.

`docs/ml/MODEL_CARDS.md` — PaddleOCR PP-OCRv5 (Apache-2.0), exact installed version (from Task 7 Step 1), model-card URL, runtime (CPU container / GPU dev), and a "Results" section left to be filled only from stored benchmark JSON.

- [ ] **Step 9: Commit**

```bash
git add apps/ml-service/app/bench_eval.py apps/ml-service/bench/ apps/ml-service/tests/test_ocr_eval.py docs/ml/
git commit -m "add OCR benchmark harness and dataset/model-card register"
```

---

## Final verification

- [ ] Run the full ml-service suite: `cd apps/ml-service && python -m pytest -q` → all green.
- [ ] Run the api suite to confirm the contract still holds: `cd apps/api && ./.venv/Scripts/python.exe -m pytest -q` → all green (document()/consultation flow unaffected; flag is off by default).
- [ ] Confirm `ML_OCR_ENABLED` unset ⇒ byte-identical stub behavior; set true in a scratch run ⇒ additive fields present.
- [ ] Confirm no raw report content is logged anywhere added.

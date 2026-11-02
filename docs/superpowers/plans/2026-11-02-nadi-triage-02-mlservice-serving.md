# Phase 2 — ml-service Triage Serving Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve the trained BiLSTM specialty classifier from `ml-service` behind `ML_TRIAGE_ENABLED` (default OFF), loading the Phase 1 ONNX artifacts with onnxruntime, with a never-raise fallback.

**Architecture:** New `app/triage_model/` package — `normalize` (shared text cleanup), `infer` (lazy onnxruntime singleton), `pipeline` (`run()` producing the specialty-only contract, never raises). The `/ml/v1/triage` route calls `pipeline.run` when the flag is on, else the specialty-only stub (`triage_stub.run` from Phase 5). onnxruntime is added to the container; **TensorFlow is not** (training is Colab-only).

**Tech Stack:** Python/FastAPI, onnxruntime, numpy.

## Global Constraints

- No AI attribution in any committed artefact.
- `ML_TRIAGE_ENABLED` defaults **OFF**; OFF path = `triage_stub.run` (specialty-only after Phase 5).
- `pipeline.run` **never raises** — on any error (missing artifact, bad input) it returns a safe default specialty, mirroring `app/ocr/pipeline.py`.
- Contract (both paths): `{ "specialties": [{"name","score"}], "labs": [...], "modelVersion": str }`.
- Depends on **Phase 5** (stub is already specialty-only) and, for flag-ON real predictions, on **Phase 1** artifacts committed to `app/triage_model/artifacts/`.
- ml-service tests: `cd apps/ml-service && ./.venv/Scripts/python.exe -m pytest`.

---

### Task 1: Config flag + normalizer

**Files:**
- Modify: `apps/ml-service/app/config.py`
- Create: `apps/ml-service/app/triage_model/__init__.py` (empty)
- Create: `apps/ml-service/app/triage_model/normalize.py`
- Test: `apps/ml-service/tests/test_triage_normalize.py` (new)

**Interfaces:**
- Produces: `settings.ml_triage_enabled: bool` (default False); `normalize.clean(text: str) -> str` (lowercase, collapse whitespace, strip).

- [ ] **Step 1: Write the failing test**

```python
# apps/ml-service/tests/test_triage_normalize.py
from app.triage_model.normalize import clean


def test_clean_lowercases_and_collapses_whitespace():
    assert clean("  Chest   PAIN\n") == "chest pain"


def test_clean_empty():
    assert clean("") == ""
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd apps/ml-service && ./.venv/Scripts/python.exe -m pytest tests/test_triage_normalize.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

```python
# apps/ml-service/app/triage_model/normalize.py
import re

_WS = re.compile(r"\s+")


def clean(text: str) -> str:
    return _WS.sub(" ", text.strip().lower())
```
Add to `apps/ml-service/app/config.py` `Settings`:
```python
    # Trained triage model off until artifacts land + validated; off == keyword stub.
    ml_triage_enabled: bool = False
```
Create empty `apps/ml-service/app/triage_model/__init__.py`.

- [ ] **Step 4: Run the test**

Run: `cd apps/ml-service && ./.venv/Scripts/python.exe -m pytest tests/test_triage_normalize.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/ml-service/app/config.py apps/ml-service/app/triage_model/
git commit -m "ml-service: triage_model package scaffold + ML_TRIAGE_ENABLED flag + normalizer"
```

---

### Task 2: inference loader (lazy onnxruntime) + pipeline (never-raise)

**Files:**
- Modify: `apps/ml-service/pyproject.toml` (add `onnxruntime`)
- Create: `apps/ml-service/app/triage_model/infer.py`
- Create: `apps/ml-service/app/triage_model/pipeline.py`
- Test: `apps/ml-service/tests/test_triage_pipeline.py` (new)

**Interfaces:**
- Consumes: `normalize.clean` (Task 1).
- Produces:
  - `infer.predict(text: str) -> list[dict]` — top specialties `[{"name","score"}]`; raises if artifacts are absent (callers must guard).
  - `infer.ARTIFACT_DIR` = `app/triage_model/artifacts`; `infer.available() -> bool`.
  - `pipeline.run(symptom_text, labs, age, sex) -> dict` — the full contract; **never raises**; `MODEL_VERSION = "triage-bilstm-v1"`.

- [ ] **Step 1: Write the failing test** (works with OR without artifacts)

```python
# apps/ml-service/tests/test_triage_pipeline.py
import pytest
from app.triage_model import infer, pipeline


def test_run_returns_contract_shape_even_without_model():
    r = pipeline.run("chest pain", [], 50, "M")
    assert set(r.keys()) == {"specialties", "labs", "modelVersion"}
    assert r["modelVersion"] == pipeline.MODEL_VERSION
    assert isinstance(r["specialties"], list) and r["specialties"]
    assert all({"name", "score"} <= set(s) for s in r["specialties"])


def test_run_passes_labs_through():
    labs = [{"analyte": "Hb", "value": 9.1, "unit": "g/dL", "refRange": "12-15", "flag": "L"}]
    assert pipeline.run("tired", labs, 40, "F")["labs"] == labs


@pytest.mark.skipif(not infer.available(), reason="ONNX artifacts not present yet")
def test_predict_real_specialty_for_known_symptom():
    specs = infer.predict("itchy rash on my skin")
    assert specs[0]["name"]  # a real specialty string
    assert 0.0 <= specs[0]["score"] <= 1.0
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd apps/ml-service && ./.venv/Scripts/python.exe -m pytest tests/test_triage_pipeline.py -v`
Expected: FAIL — modules missing (the skip-marked test is skipped).

- [ ] **Step 3: Add the dependency**

In `apps/ml-service/pyproject.toml`, append `"onnxruntime>=1.17"` to the `dependencies` list.
Install into the venv: `cd apps/ml-service && ./.venv/Scripts/python.exe -m pip install onnxruntime`.

- [ ] **Step 4: Implement `infer.py`**

```python
# apps/ml-service/app/triage_model/infer.py
import json
from pathlib import Path

from app.triage_model.normalize import clean

ARTIFACT_DIR = Path(__file__).parent / "artifacts"
_MODEL = ARTIFACT_DIR / "triage_bilstm.onnx"
_LABELS = ARTIFACT_DIR / "specialty_labels.json"

_session = None
_labels: list[str] | None = None


def available() -> bool:
    return _MODEL.exists() and _LABELS.exists()


def _load():
    global _session, _labels
    if _session is None:
        import numpy as np  # noqa: F401  (ensure present)
        import onnxruntime as ort

        _session = ort.InferenceSession(str(_MODEL), providers=["CPUExecutionProvider"])
        _labels = json.loads(_LABELS.read_text(encoding="utf-8"))
    return _session, _labels


def predict(text: str, top_k: int = 3) -> list[dict]:
    import numpy as np

    session, labels = _load()
    # The exported graph bakes in TextVectorization: input is a raw string tensor.
    inp = session.get_inputs()[0]
    feed = {inp.name: np.array([[clean(text)]], dtype=object) if "string" in inp.type
            else np.array([clean(text)], dtype=object)}
    probs = session.run(None, feed)[0][0]
    order = probs.argsort()[::-1][:top_k]
    return [{"name": labels[i], "score": round(float(probs[i]), 4)} for i in order]
```
> If Phase 1 exports the vocab separately instead of baking `TextVectorization` into the graph,
> replace the feed construction with the documented vectorization fallback (load
> `artifacts/vocab.json`, map tokens→ids, pad). The `predict` signature stays the same.

- [ ] **Step 5: Implement `pipeline.py`**

```python
# apps/ml-service/app/triage_model/pipeline.py
from app.triage_model import infer

MODEL_VERSION = "triage-bilstm-v1"
_DEFAULT = [
    {"name": "General Physician", "score": 0.6},
    {"name": "General Medicine", "score": 0.25},
    {"name": "ENT", "score": 0.15},
]


def run(symptom_text: str, labs: list[dict], age, sex) -> dict:
    try:
        specialties = infer.predict(symptom_text) if infer.available() else _DEFAULT
    except Exception:
        specialties = _DEFAULT
    return {"specialties": specialties, "labs": labs, "modelVersion": MODEL_VERSION}
```

- [ ] **Step 6: Run the tests**

Run: `cd apps/ml-service && ./.venv/Scripts/python.exe -m pytest tests/test_triage_pipeline.py -v`
Expected: PASS (real-prediction test SKIPPED until artifacts exist).

- [ ] **Step 7: Commit**

```bash
git add apps/ml-service/pyproject.toml apps/ml-service/app/triage_model/infer.py apps/ml-service/app/triage_model/pipeline.py apps/ml-service/tests/test_triage_pipeline.py
git commit -m "ml-service: onnxruntime triage inference + never-raise pipeline"
```

---

### Task 3: wire the flag into `/ml/v1/triage`

**Files:**
- Modify: `apps/ml-service/app/main.py`
- Test: `apps/ml-service/tests/test_triage_route.py` (new)

**Interfaces:**
- Consumes: `settings.ml_triage_enabled`, `triage_pipeline.run`, `triage_stub.run`.

- [ ] **Step 1: Write the failing test**

```python
# apps/ml-service/tests/test_triage_route.py
from fastapi.testclient import TestClient
from app.config import settings
from app.main import app

client = TestClient(app)
PAYLOAD = {"symptomText": "itchy rash", "labs": [], "age": 30, "sex": "F", "lang": "en"}


def test_flag_off_uses_stub(monkeypatch):
    monkeypatch.setattr(settings, "ml_triage_enabled", False)
    r = client.post("/ml/v1/triage", json=PAYLOAD)
    assert r.status_code == 200
    assert r.json()["modelVersion"] == "stub-keyword-v0"
    assert set(r.json().keys()) == {"specialties", "labs", "modelVersion"}


def test_flag_on_uses_model(monkeypatch):
    monkeypatch.setattr(settings, "ml_triage_enabled", True)
    r = client.post("/ml/v1/triage", json=PAYLOAD)
    assert r.status_code == 200
    assert r.json()["modelVersion"] == "triage-bilstm-v1"
    assert set(r.json().keys()) == {"specialties", "labs", "modelVersion"}
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd apps/ml-service && ./.venv/Scripts/python.exe -m pytest tests/test_triage_route.py -v`
Expected: FAIL — `test_flag_on_uses_model` gets `stub-keyword-v0` (flag not wired).

- [ ] **Step 3: Edit `app/main.py`**

```python
from app.triage_model import pipeline as triage_pipeline
# ...
@app.post("/ml/v1/triage")
def triage(req: TriageRequest) -> dict:
    labs = [lab.model_dump() for lab in req.labs]
    if settings.ml_triage_enabled:
        return triage_pipeline.run(req.symptomText, labs, req.age, req.sex)
    return run(req.symptomText, labs, req.age, req.sex)
```
Also update `/ml/v1/health` `modelVersions` to include `"triageModel": triage_pipeline.MODEL_VERSION` (optional, nice-to-have).

- [ ] **Step 4: Run the tests**

Run: `cd apps/ml-service && ./.venv/Scripts/python.exe -m pytest tests/test_triage_route.py -v`
Expected: PASS (flag-on uses the never-raise pipeline → `_DEFAULT` specialties when artifacts absent, correct `modelVersion`).

- [ ] **Step 5: Commit**

```bash
git add apps/ml-service/app/main.py apps/ml-service/tests/test_triage_route.py
git commit -m "ml-service: /ml/v1/triage honors ML_TRIAGE_ENABLED"
```

---

### Task 4: container + compose flag plumbing

**Files:**
- Modify: `apps/ml-service/Dockerfile` (ensure onnxruntime installs; it is in pyproject so `pip install .` covers it — no system libs needed)
- Modify: `infra/docker-compose.yml` (pass `ML_TRIAGE_ENABLED` to the ml-service service, default false)
- Modify: `infra/.env.example` (document `ML_TRIAGE_ENABLED=false`)

- [ ] **Step 1: Add the env var** to the `ml-service` service in `infra/docker-compose.yml`:
```yaml
      ML_TRIAGE_ENABLED: ${ML_TRIAGE_ENABLED:-false}
```
Add `ML_TRIAGE_ENABLED=false` to `infra/.env.example` with a comment.

- [ ] **Step 2: Rebuild + verify flag-off health**

Run:
```bash
docker compose -f infra/docker-compose.yml up -d --build ml-service
curl -s http://localhost:8001/ml/v1/health   # or the mapped ml-service port
```
Expected: healthy; default flag off.

- [ ] **Step 3: Commit**

```bash
git add apps/ml-service/Dockerfile infra/docker-compose.yml infra/.env.example
git commit -m "ml-service: plumb ML_TRIAGE_ENABLED through compose (default off)"
```

---

### Task 5: artifact smoke test (runs once Phase 1 artifacts are committed)

**Files:**
- Test: `apps/ml-service/tests/test_triage_artifacts.py` (new)

- [ ] **Step 1: Add the smoke test**

```python
# apps/ml-service/tests/test_triage_artifacts.py
import pytest
from app.triage_model import infer


@pytest.mark.skipif(not infer.available(), reason="ONNX artifacts not committed yet")
def test_onnx_loads_and_predicts():
    out = infer.predict("fever and cough")
    assert out and out[0]["name"]
    # The predicted label is one of the known specialties.
    import json
    labels = set(json.loads((infer.ARTIFACT_DIR / "specialty_labels.json").read_text()))
    assert out[0]["name"] in labels
```

- [ ] **Step 2: Run** (skips until artifacts exist)

Run: `cd apps/ml-service && ./.venv/Scripts/python.exe -m pytest tests/test_triage_artifacts.py -v`
Expected: SKIPPED now; PASS after Phase 1 artifacts are committed and `ML_TRIAGE_ENABLED` validated.

- [ ] **Step 3: Commit**

```bash
git add apps/ml-service/tests/test_triage_artifacts.py
git commit -m "ml-service: triage ONNX artifact smoke test (skips until artifacts land)"
```

## Self-review notes
- Spec Phase 2 coverage: flag + normalizer (T1), onnxruntime infer + never-raise pipeline (T2), route wiring (T3), container/compose (T4), artifact smoke (T5). Covered.
- The flag-ON real-prediction path is only fully exercised once Phase 1's ONNX + labels are committed; until then flag-ON returns the never-raise `_DEFAULT` with the correct `modelVersion`, which the route test asserts.
- `TextVectorization`-baked-in assumption has a documented fallback in `infer.predict` (Step 4 note) matching the spec's ONNX-export risk.

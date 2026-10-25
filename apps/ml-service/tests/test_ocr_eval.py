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

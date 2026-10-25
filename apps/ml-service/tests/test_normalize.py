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

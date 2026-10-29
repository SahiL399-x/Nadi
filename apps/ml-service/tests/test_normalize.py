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


def test_data_vocab_maps_uncurated_analyte_with_loinc():
    # Procalcitonin is NOT a hand-curated alias; it comes from the
    # NidaanKosha-derived vocab, with a LOINC code attached.
    res = normalize_fields([_raw("PROCALCITONIN", "67.07", "ng/mL")])
    f = res["fields"][0]
    assert f["testNameNormalized"] == "Procalcitonin"
    assert f["loinc"] == "33959-8"
    assert "unknown_analyte" not in f["qualityFlags"]


def test_curated_alias_overrides_data_vocab():
    # The vocab canonical for HEMOGLOBIN is "Hemoglobin"; the curated alias
    # ("Haemoglobin") must take precedence.
    res = normalize_fields([_raw("HEMOGLOBIN", "9.1", "g/dL")])
    assert res["fields"][0]["testNameNormalized"] == "Haemoglobin"


def test_unknown_analyte_kept_raw_with_empty_loinc():
    res = normalize_fields([_raw("ZZQ RANDOM LABEL", "5.0")])
    f = res["fields"][0]
    assert f["testNameNormalized"] == "ZZQ RANDOM LABEL"
    assert f["loinc"] == ""
    assert "unknown_analyte" in f["qualityFlags"]


def test_data_vocab_unit_mismatch_is_not_warned():
    # Source units are noisy (gm/dl vs g/dL), so vocab-derived entries must NOT
    # raise spurious unit_mismatch warnings (only curated aliases do).
    res = normalize_fields([_raw("PROCALCITONIN", "67.07", "something-odd")])
    assert "unit_mismatch" not in res["fields"][0]["qualityFlags"]
    assert not any("unit" in w for w in res["warnings"])

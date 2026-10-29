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


def test_tall_row_on_highres_scan_groups_name_and_value():
    # Regression: on a ~4000px-tall scan (~60px text), cells in ONE logical row
    # have y-midpoints ~30px apart. The old fixed 14px bucket split the name and
    # value into separate rows and dropped both (62/218 real images parsed 0
    # fields despite good OCR). Row grouping must scale with text height.
    lines = [
        _line("Procalcitonin assay", 90, 1031, w=911, h=63),
        _line("67.07", 1197, 1065, w=150, h=60),
        _line("High", 1597, 1065, w=125, h=73),
        _line("0-0.05", 2396, 1068, w=166, h=58),
    ]
    fields = parse_fields(lines)
    assert len(fields) == 1
    f = fields[0]
    assert f["testNameRaw"] == "Procalcitonin assay"
    assert f["valueRaw"] == "67.07"
    assert f["referenceRangeRaw"] == "0-0.05"


def test_densely_packed_rows_stay_separate():
    # The adaptive grouping must NOT over-merge: tightly spaced small-text rows
    # (~28px tall, ~32px apart) must remain distinct tests.
    lines = [
        _line("Specific Gravity", 68, 702, w=158, h=30), _line("1.010", 589, 694, w=62, h=26),
        _line("Albumin", 65, 799, w=88, h=24), _line("5.2", 590, 787, w=44, h=27),
    ]
    fields = parse_fields(lines)
    assert [f["testNameRaw"] for f in fields] == ["Specific Gravity", "Albumin"]

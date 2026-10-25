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

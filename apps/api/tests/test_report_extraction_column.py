from app.models import Report


def test_report_has_extraction_json_column():
    assert "extraction_json" in Report.__table__.columns
    assert Report.__table__.columns["extraction_json"].nullable is True

from sqlalchemy import inspect

from app.core.db import engine


def test_triage_results_has_no_acuity_columns():
    cols = {c["name"] for c in inspect(engine).get_columns("triage_results")}
    assert "acuity" not in cols
    assert "acuity_confidence" not in cols
    assert "red_flags" not in cols
    assert "drivers" not in cols
    assert {"specialties", "labs", "model_version"} <= cols

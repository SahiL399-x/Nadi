from sqlalchemy import inspect
from app.core.db import engine


def test_doctors_has_keywords_column():
    cols = {c["name"] for c in inspect(engine).get_columns("doctors")}
    assert "keywords" in cols

from sqlalchemy import inspect

from app.core.db import engine


def test_core_tables_exist():
    tables = set(inspect(engine).get_table_names())
    expected = {
        "users", "patients", "doctors", "pharmacies", "consultations",
        "reports", "lab_values", "triage_results", "referrals",
        "prescriptions", "prescription_lines", "pharmacy_consents",
        "pharmacy_offers", "audit_log",
    }
    assert expected.issubset(tables)

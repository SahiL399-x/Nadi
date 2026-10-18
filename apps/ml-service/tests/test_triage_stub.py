from app.triage_stub import run


def test_chest_breath_is_emergency_with_redflag():
    r = run("chest pain and breathlessness", [], 50, "M")
    assert r["acuity"] == "EMERGENCY"
    assert r["redFlags"]
    assert r["modelVersion"] == "stub-keyword-v0"


def test_chakkar_is_priority_general_medicine():
    r = run("mujhe chakkar aa raha hai", [], 30, "F")
    assert r["acuity"] == "PRIORITY"
    assert r["specialties"][0]["name"] == "General Medicine"


def test_fever_is_routine():
    r = run("fever and cough", [], 25, "M")
    assert r["acuity"] == "ROUTINE"


def test_specialties_always_length_three_descending():
    r = run("something unmapped", [], 40, "M")
    scores = [s["score"] for s in r["specialties"]]
    assert len(r["specialties"]) == 3
    assert scores == sorted(scores, reverse=True)

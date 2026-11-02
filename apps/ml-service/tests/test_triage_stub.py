from app.triage_stub import run


def test_skin_routes_to_dermatology():
    r = run("itchy rash on my arm", [], 28, "F")
    assert r["specialties"][0]["name"] == "Dermatology"


def test_chakkar_routes_to_general_medicine():
    r = run("mujhe chakkar aa raha hai", [], 30, "F")
    assert r["specialties"][0]["name"] == "General Medicine"


def test_chest_routes_to_cardiology():
    r = run("chest pain since morning", [], 45, "M")
    assert r["specialties"][0]["name"] == "Cardiology"


def test_contract_is_specialty_only():
    r = run("fever and cough", [], 25, "M")
    assert set(r.keys()) == {"specialties", "labs", "modelVersion"}
    assert r["modelVersion"] == "stub-keyword-v0"


def test_specialties_length_three_descending():
    r = run("something unmapped", [], 40, "M")
    scores = [s["score"] for s in r["specialties"]]
    assert len(r["specialties"]) == 3
    assert scores == sorted(scores, reverse=True)


def test_labs_passthrough():
    labs = [{"analyte": "Hb", "value": 9.1, "unit": "g/dL", "refRange": "12-15", "flag": "L"}]
    r = run("tired", labs, 40, "F")
    assert r["labs"] == labs

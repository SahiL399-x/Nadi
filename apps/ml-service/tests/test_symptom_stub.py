from app.symptom_stub import normalise


def test_normalise_returns_entities_and_string():
    out = normalise("mujhe pet me jalan ho rahi hai")
    assert "entities" in out
    assert isinstance(out["normalised"], str)
    assert out["normalised"]

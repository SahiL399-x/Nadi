from app.redflags import check


def test_chest_pain_with_breathlessness_fires():
    assert check("mujhe chest pain aur breathlessness ho raha hai")


def test_seizure_fires():
    assert "seizure" in " ".join(check("patient had a seizure")).lower()


def test_plain_fever_does_not_fire():
    assert check("mild fever since morning") == []

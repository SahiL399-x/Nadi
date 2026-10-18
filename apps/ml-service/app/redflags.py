RULES: list[tuple[str, list[list[str]]]] = [
    ("chest pain with breathlessness", [["chest", "breath"], ["seene", "saans"]]),
    ("one-sided weakness or slurred speech", [["one-sided", "weak"], ["slurred"], ["paralysis"]]),
    ("seizure", [["seizure"], ["convulsion"], ["fit", "jhatka"]]),
    ("severe bleeding", [["severe", "bleeding"], ["heavy", "blood"]]),
    ("unresponsiveness", [["unconscious"], ["unresponsive"], ["behosh"]]),
    ("bleeding during pregnancy", [["pregnan", "bleed"], ["garbh", "khoon"]]),
    ("high fever in an infant", [["infant", "fever"], ["newborn", "fever"], ["baby", "high fever"]]),
]


def check(text: str) -> list[str]:
    t = text.lower()
    fired: list[str] = []
    for label, groups in RULES:
        for group in groups:
            if all(token in t for token in group):
                fired.append(label)
                break
    return fired

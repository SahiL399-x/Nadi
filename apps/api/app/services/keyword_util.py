def normalize_keywords(raw: list[str], cap: int = 15) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        k = item.strip().lower()
        if k and k not in seen:
            seen.add(k)
            out.append(k)
        if len(out) >= cap:
            break
    return out

import re

_NUM = re.compile(r"^[<>]?\d+(?:\.\d+)?$")
_RANGE = re.compile(r"\d+(?:\.\d+)?\s*[-–]\s*\d+(?:\.\d+)?")


def _row_key(box: list[int]) -> int:
    # Group by vertical band: midpoint bucketed to tolerate small y jitter.
    return (box[1] + box[3] // 2) // 14


def _bbox(boxes: list[list[int]]) -> list[int]:
    x0 = min(b[0] for b in boxes)
    y0 = min(b[1] for b in boxes)
    x1 = max(b[0] + b[2] for b in boxes)
    y1 = max(b[1] + b[3] for b in boxes)
    return [x0, y0, x1 - x0, y1 - y0]


def parse_fields(lines: list[dict]) -> list[dict]:
    rows: dict[int, list[dict]] = {}
    for ln in lines:
        rows.setdefault(_row_key(ln["box"]), []).append(ln)

    out: list[dict] = []
    for key in sorted(rows):
        cells = sorted(rows[key], key=lambda c: c["box"][0])
        texts = [c["text"].strip() for c in cells]

        value_idx = next((i for i, t in enumerate(texts) if _NUM.match(t)), None)
        if value_idx is None or value_idx == 0:
            continue  # no numeric value, or nothing to the left to name it

        name = " ".join(texts[:value_idx]).strip()
        value_raw = texts[value_idx].lstrip("<>")
        rest = texts[value_idx + 1 :]
        rng_match = next((m.group(0) for t in rest if (m := _RANGE.search(t))), "")
        unit = next((t for t in rest if not _RANGE.search(t) and not _NUM.match(t)), "")

        out.append({
            "testNameRaw": name,
            "valueRaw": value_raw,
            "unitRaw": unit,
            "referenceRangeRaw": rng_match,
            "sourceRegion": _bbox([c["box"] for c in cells]),
            "conf": min(c["conf"] for c in cells),
        })
    return out

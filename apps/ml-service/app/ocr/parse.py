import re
from statistics import median

_NUM = re.compile(r"^[<>]?\d+(?:\.\d+)?$")
_RANGE = re.compile(r"\d+(?:\.\d+)?\s*[-–]\s*\d+(?:\.\d+)?")


def _ymid(box: list[int]) -> int:
    return box[1] + box[3] // 2


def _group_rows(lines: list[dict]) -> list[list[dict]]:
    """Cluster OCR lines into visual rows by vertical position.

    Resolution-adaptive: the row tolerance scales with the median text height,
    so a single logical row's cells stay together whether the scan is 300px or
    4000px tall. A previous fixed 14px bucket shattered rows on high-resolution
    scans — a row's name and value land ~30px apart and fell into different
    buckets, so both were dropped (62/218 real lab images parsed zero fields
    despite good OCR). Grouping by the first (topmost) line's midpoint as the
    row anchor avoids chaining-drift that would over-merge adjacent rows.
    """
    if not lines:
        return []
    tol = max(median(ln["box"][3] for ln in lines) * 0.7, 10.0)
    ordered = sorted(lines, key=lambda ln: _ymid(ln["box"]))
    rows: list[list[dict]] = []
    current = [ordered[0]]
    anchor = _ymid(ordered[0]["box"])
    for ln in ordered[1:]:
        if _ymid(ln["box"]) - anchor <= tol:
            current.append(ln)
        else:
            rows.append(current)
            current = [ln]
            anchor = _ymid(ln["box"])
    rows.append(current)
    return rows


def _bbox(boxes: list[list[int]]) -> list[int]:
    x0 = min(b[0] for b in boxes)
    y0 = min(b[1] for b in boxes)
    x1 = max(b[0] + b[2] for b in boxes)
    y1 = max(b[1] + b[3] for b in boxes)
    return [x0, y0, x1 - x0, y1 - y0]


def parse_fields(lines: list[dict]) -> list[dict]:
    out: list[dict] = []
    for row in _group_rows(lines):
        cells = sorted(row, key=lambda c: c["box"][0])
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

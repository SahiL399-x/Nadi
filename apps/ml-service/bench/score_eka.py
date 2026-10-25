"""Score OCR predictions against rubric-derived gold for the Eka lab-report set.

Runs on the host (no paddle needed). Honest, diagnostic metrics that separate
"OCR couldn't read it" from "our parser/dictionary missed it":

  ocr_name_in_text  : gold test name's distinctive token appears in raw OCR text  (recognition)
  ocr_value_in_text : gold value string appears in raw OCR text                   (recognition)
  name_recall       : a parsed field's name matches the gold test name            (recognition+parse)
  value_recall      : a name-matched parsed field also has a matching value       (end-to-end extraction)

The gap (ocr_*_in_text  >  name_recall/value_recall) is parser/dict loss, not OCR loss.

Usage: python bench/score_eka.py <gold.json> <predictions.json> [out_results.json]
"""
import json
import re
import sys

_TOKEN = re.compile(r"[A-Z0-9]+")
_GENERIC = {"TOTAL", "DIRECT", "INDIRECT", "SERUM", "BLOOD", "TEST", "COUNT", "LEVEL",
            "RATIO", "AVERAGE", "MEAN", "VALUE", "AND", "THE", "OF", "IN"}


def _tokens(name: str) -> set[str]:
    return {t for t in _TOKEN.findall((name or "").upper()) if len(t) >= 2}


def _name_match(gold: str, pred: str) -> bool:
    a, b = _tokens(gold), _tokens(pred)
    if not a or not b:
        return False
    inter = a & b
    if not inter:
        return False
    # require at least half the smaller token set to overlap, and the overlap to
    # include a non-generic (distinctive) token so TOTAL/DIRECT variants don't collide.
    if not (inter - _GENERIC):
        return False
    return len(inter) / min(len(a), len(b)) >= 0.5


def _value_match(gold_values: list[str], pred_raw: str, pred_num) -> bool:
    for gv in gold_values:
        gv = str(gv).strip()
        if not gv:
            continue
        if pred_raw is not None and str(pred_raw).strip() == gv:
            return True
        try:
            if pred_num is not None and abs(float(pred_num) - float(gv)) < 1e-6:
                return True
        except ValueError:
            pass
    return False


def _distinctive(name: str) -> list[str]:
    return [t for t in _tokens(name) if len(t) >= 4 and t not in _GENERIC]


def main() -> None:
    gold = json.load(open(sys.argv[1], encoding="utf-8"))
    preds = json.load(open(sys.argv[2], encoding="utf-8"))

    tot = {"ocr_name_in_text": 0, "ocr_value_in_text": 0, "name_recall": 0, "value_recall": 0}
    n_tests = 0
    macro = {k: [] for k in tot}
    rows_scored = 0

    for md5, g in gold.items():
        gtests = g.get("gold", [])
        if not gtests:
            continue
        pred = preds.get(md5, {"raw_ocr_text": "", "fields": []})
        text_u = (pred.get("raw_ocr_text") or "").upper()
        fields = pred.get("fields", [])
        row_hits = {k: 0 for k in tot}
        for gt in gtests:
            n_tests += 1
            name = gt.get("test_name", "")
            gvals = gt.get("values") or ([gt.get("value")] if gt.get("value") else [])

            dist = _distinctive(name)
            if dist and any(d in text_u for d in dist):
                tot["ocr_name_in_text"] += 1; row_hits["ocr_name_in_text"] += 1
            if any(str(v).strip() and str(v).strip().upper() in text_u for v in gvals):
                tot["ocr_value_in_text"] += 1; row_hits["ocr_value_in_text"] += 1

            matched = [f for f in fields if _name_match(name, f.get("testNameRaw", ""))]
            if matched:
                tot["name_recall"] += 1; row_hits["name_recall"] += 1
                if any(_value_match(gvals, f.get("valueRaw"), f.get("valueNumeric")) for f in matched):
                    tot["value_recall"] += 1; row_hits["value_recall"] += 1

        for k in tot:
            macro[k].append(row_hits[k] / len(gtests))
        rows_scored += 1

    def pct(x, n):
        return round(100 * x / n, 1) if n else 0.0

    result = {
        "n_lab_rows": rows_scored,
        "n_gold_tests": n_tests,
        "micro_pct": {k: pct(tot[k], n_tests) for k in tot},
        "macro_pct": {k: round(100 * sum(v) / len(v), 1) if v else 0.0 for k, v in macro.items()},
        "counts": tot,
        "method": "rubric-derived gold; name match = >=50% token overlap incl. a distinctive token; "
                  "value match = exact string or float-equal vs any gold value; "
                  "ocr_*_in_text = gold name/value appears in raw recognized text (recognition signal).",
    }
    print(json.dumps(result, indent=2))
    if len(sys.argv) > 3:
        json.dump(result, open(sys.argv[3], "w", encoding="utf-8"), indent=2)


if __name__ == "__main__":
    main()

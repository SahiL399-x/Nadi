from app.ocr.normalize import normalize_fields
from app.ocr.parse import parse_fields


def cer(pred: str, truth: str) -> float:
    # Levenshtein distance / len(truth), clamped to [0, 1].
    if not truth:
        return 0.0 if not pred else 1.0
    m, n = len(truth), len(pred)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, n + 1):
            cur = dp[j]
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + (truth[i - 1] != pred[j - 1]))
            prev = cur
    return min(1.0, dp[n] / m)


def evaluate(manifest: list[dict], ocr_fn=None) -> dict:
    # Each manifest item provides pre-computed OCR `lines` (fixtures/tests) OR,
    # in a real run, the CLI supplies ocr_fn to produce lines from an image.
    n = num_ok = unit_ok = pair_ok = 0
    cers: list[float] = []
    for item in manifest:
        lines = item["lines"] if ocr_fn is None else ocr_fn(item["image_path"])
        fields = normalize_fields(parse_fields(lines))["fields"]
        by_name = {f["testNameNormalized"]: f for f in fields}
        for truth in item["truth"]:
            n += 1
            got = by_name.get(truth["analyte"])
            if got and got["valueNumeric"] == truth["value"]:
                num_ok += 1
            if got and got["unit"].lower() == truth["unit"].lower():
                unit_ok += 1
            if got and got["valueNumeric"] == truth["value"] and got["flag"] == truth["flag"]:
                pair_ok += 1
            cers.append(cer(got["testNameNormalized"] if got else "", truth["analyte"]))
    return {
        "n": n,
        "numeric_accuracy": (num_ok / n) if n else 0.0,
        "unit_accuracy": (unit_ok / n) if n else 0.0,
        "pairing_accuracy": (pair_ok / n) if n else 0.0,
        "field_exact_match": (pair_ok / n) if n else 0.0,
        "cer": (sum(cers) / len(cers)) if cers else 0.0,
        "mean_latency_ms": 0,
    }

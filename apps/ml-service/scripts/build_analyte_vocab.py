"""One-time OFFLINE build of the analyte normalization vocabulary.

Source: ekacare/NidaanKosha-100k-V1.0 (CC-BY-SA-4.0) — 6.8M real lab readings.
Run with a Python that has huggingface_hub + pandas + pyarrow (NOT the
ml-service runtime venv, which stays dependency-light):

    python scripts/build_analyte_vocab.py

Output: app/ocr/data/analyte_vocab.json — maps a normalized test-name variant
to {canonical, loinc, unit}. The LOINC code is the canonical key: all name
variants sharing a LOINC are synonyms of one analyte. A variant is included
only if it is frequent enough AND unambiguously tied to a single LOINC (guards
against mislabeling, since normalize.py does exact-match-only lookup).

The normalization MUST stay byte-identical to normalize._canon_key.
"""
import json
import re
from pathlib import Path

import pandas as pd
from huggingface_hub import hf_hub_download

REPO = "ekacare/NidaanKosha-100k-V1.0"
SHARDS = ("data/train-00000-of-00002.parquet", "data/train-00001-of-00002.parquet")
MIN_FREQ = 10          # a variant must appear >= this many times across 6.8M rows
MIN_LOINC_SHARE = 0.6  # >= this fraction of a variant's rows must share one LOINC
OUT = Path(__file__).resolve().parent.parent / "app" / "ocr" / "data" / "analyte_vocab.json"


def canon_key(name: str) -> str:
    # Keep letters/digits and clinically meaningful symbols; collapse the rest.
    cleaned = re.sub(r"[^A-Z0-9()%/.\-+ ]", " ", str(name).upper())
    return re.sub(r"\s+", " ", cleaned).strip()


def main() -> None:
    frames = [pd.read_parquet(hf_hub_download(REPO, s, repo_type="dataset"),
                              columns=["test_name", "unit", "loinc"]) for s in SHARDS]
    df = pd.concat(frames, ignore_index=True)
    # Normalize to plain python strings up front: the source uses pandas' nullable
    # "str" dtype, where NA propagates through comparisons and value_counts() drops
    # it — which blew up idxmax() on all-missing groups. Collapse NA -> "" here.
    for col in ("test_name", "unit", "loinc"):
        df[col] = df[col].astype("string").fillna("").map(str).str.strip()

    df = df[df["loinc"] != ""]
    df["key"] = df["test_name"].map(canon_key)
    df = df[df["key"] != ""]

    def _mode(series) -> str:
        counts = series[series != ""].value_counts()
        return str(counts.idxmax()) if not counts.empty else ""

    vocab: dict[str, dict] = {}
    kept = dropped_rare = dropped_ambig = 0
    for key, grp in df.groupby("key", sort=False):
        if len(grp) < MIN_FREQ:
            dropped_rare += 1
            continue
        loinc_counts = grp["loinc"].value_counts()
        top_loinc = str(loinc_counts.idxmax())
        if loinc_counts.max() / len(grp) < MIN_LOINC_SHARE:
            dropped_ambig += 1
            continue
        sub = grp[grp["loinc"] == top_loinc]
        canonical = _mode(sub["test_name"])
        if not canonical:
            dropped_rare += 1
            continue
        vocab[key] = {"canonical": canonical, "loinc": top_loinc, "unit": _mode(sub["unit"])}
        kept += 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(vocab, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"entries: {kept} | dropped rare: {dropped_rare} | dropped ambiguous: {dropped_ambig}")
    print(f"file size: {OUT.stat().st_size/1024:.0f} KB")


if __name__ == "__main__":
    main()

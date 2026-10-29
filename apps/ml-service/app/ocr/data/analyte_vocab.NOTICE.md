# analyte_vocab.json — attribution & license

`analyte_vocab.json` is a derived work (a LOINC-anchored synonym → canonical
analyte map) built from:

> **NidaanKosha-100k-V1.0** by **Eka Care**
> https://huggingface.co/datasets/ekacare/NidaanKosha-100k-V1.0
> Licensed under **CC-BY-SA-4.0** (https://creativecommons.org/licenses/by-sa/4.0/)

In accordance with CC-BY-SA-4.0, this derived vocabulary is distributed under
the **same license (CC-BY-SA-4.0)** with attribution to Eka Care. It was
produced offline by `apps/ml-service/scripts/build_analyte_vocab.py`
(group rows by LOINC code; keep a name variant only if it appears ≥10 times and
is unambiguously tied to a single LOINC). No source images or raw parquet shards
from the dataset are redistributed.

This file contains factual test-name ↔ LOINC ↔ unit associations only. It is
used solely for display/normalization of OCR-extracted lab fields; it is never
used to train or fine-tune a model.

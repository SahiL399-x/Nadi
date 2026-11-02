# Phase 1 — Triage Training Notebook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A committed Colab notebook that trains a TF-IDF+LogReg baseline and a BiLSTM to classify a symptom query into one of NADI's ~10 specialties, on a hybrid English + Hindi/Hinglish dataset, and exports ONNX + label artifacts for Phase 2.

**Architecture:** One `.ipynb` at `apps/ml-service/notebooks/triage_rnn.ipynb`, runnable top-to-bottom on Colab free T4. Two datasets unioned via per-dataset disease→specialty maps; the trained Keras model is exported to ONNX (with `TextVectorization` baked into the graph) plus `specialty_labels.json`.

**Tech Stack:** Python, HuggingFace `datasets`, scikit-learn, TensorFlow/Keras, `tf2onnx`.

## TDD exception (explicit)

A Colab notebook cannot run in this repo's CI, and training is exploratory. Per the TDD skill's
"generated/exploratory code" exception, this phase is **not** red-green TDD. Instead every
modelling cell ends with an **`assert`** self-check, and the exported artifacts are verified by
Phase 2's `test_triage_artifacts.py` once committed. Do not claim the model "works" from this
phase alone — that claim is gated on Phase 2's artifact smoke test passing.

## Global Constraints

- No AI attribution in any committed artefact (ProjectPlan §14.11) — including notebook cells/markdown.
- **Do NOT commit the raw datasets** (load at runtime). Add dataset provenance to
  `apps/ml-service/docs/ml/DATASET_REGISTER.md` (create if absent) and a NOTICE/attribution
  entry if the Tulsiandhare license requires it.
- Predicts **specialty** (softmax) — not disease. Specialty label set is exactly NADI's seeded
  specialties: `General Physician, General Medicine, Cardiology, Dermatology, ENT, Gynaecology,
  Paediatrics, Orthopaedics, Haematology`. (No Emergency Medicine — acuity is gone.)
- Artifacts land in `apps/ml-service/app/triage_model/artifacts/`: `triage_bilstm.onnx`,
  `specialty_labels.json`, `model_card.md` (and `vocab.json` only if vectorization is NOT baked in).

---

### Task 1: Notebook scaffold + dataset-license gate

**Files:**
- Create: `apps/ml-service/notebooks/triage_rnn.ipynb`
- Create/modify: `apps/ml-service/docs/ml/DATASET_REGISTER.md`

- [ ] **Step 1: Verify the Tulsiandhare license before writing any data cell.** Open the HF
  dataset page / `README`/`LICENSE`/`croissant` metadata. Record the actual license in
  `DATASET_REGISTER.md`.
  - If permissive/research-OK for this student showpiece → proceed with the hybrid.
  - If incompatible → **fall back to gretelai-only** training + add a small romanized-Hindi→
    English lexicon (seed from the Hindi/Marathi terms in `apps/ml-service/app/triage_stub.py`)
    as the multilingual layer, and note the fallback in the notebook + register.

- [ ] **Step 2: Create the notebook with a title + setup cell**
  - Markdown cell: title "NADI Triage — Symptom → Specialty", one line on purpose ("routes, does
    not diagnose"), and a note that it trains on Colab T4.
  - Code cell (setup):
    ```python
    !pip -q install "datasets>=2.19" scikit-learn "tensorflow>=2.15" tf2onnx onnx
    import numpy as np, tensorflow as tf, json, os
    from pathlib import Path
    SEED = 42; np.random.seed(SEED); tf.random.set_seed(SEED)
    ARTIFACTS = Path("artifacts"); ARTIFACTS.mkdir(exist_ok=True)
    SPECIALTIES = ["General Physician","General Medicine","Cardiology","Dermatology",
                   "ENT","Gynaecology","Paediatrics","Orthopaedics","Haematology"]
    ```

- [ ] **Step 3: Commit the scaffold**

```bash
git add apps/ml-service/notebooks/triage_rnn.ipynb apps/ml-service/docs/ml/DATASET_REGISTER.md
git commit -m "ml: triage notebook scaffold + dataset license register"
```

---

### Task 2: Data load + disease→specialty maps + unified frame

**Files:** modify `apps/ml-service/notebooks/triage_rnn.ipynb`

- [ ] **Step 1: Load cell**
  ```python
  from datasets import load_dataset
  gret = load_dataset("gretelai/symptom_to_diagnosis", split="train").to_pandas()
  # columns: input_text (symptom), output_text (one of 22 diagnoses)
  try:
      mult = load_dataset("Tulsiandhare/Multilingual_medical_symptom_triage", split="train").to_pandas()
  except Exception as e:
      print("multilingual dataset unavailable, continuing gretelai-only:", e); mult = None
  ```

- [ ] **Step 2: Two disease→specialty dicts** (author explicitly; one per dataset's label vocab),
  mapping every label into `SPECIALTIES`. Example shape:
  ```python
  GRETEL_TO_SPECIALTY = {
      "drug reaction": "Dermatology", "allergy": "General Medicine",
      "psoriasis": "Dermatology", "diabetes": "General Medicine",
      "gastroesophageal reflux disease": "General Medicine",
      "peptic ulcer disease": "General Medicine", "bronchial asthma": "General Medicine",
      "cervical spondylosis": "Orthopaedics", "arthritis": "Orthopaedics",
      "urinary tract infection": "General Medicine", "common cold": "General Physician",
      "pneumonia": "General Medicine", "migraine": "General Medicine",
      "hypertension": "Cardiology", "varicose veins": "General Medicine",
      "malaria": "General Medicine", "dengue": "General Medicine",
      "typhoid": "General Medicine", "chicken pox": "Dermatology",
      "jaundice": "General Medicine", "fungal infection": "Dermatology",
      "impetigo": "Dermatology",
  }  # must cover all 22 labels present in gret["output_text"].unique()
  TULSI_TO_SPECIALTY = { ... }  # cover every value in mult["disease"] (or "category")
  ```

- [ ] **Step 3: Completeness assert** (the plan's safety net — no silent unmapped labels)
  ```python
  missing = set(gret["output_text"].str.lower()) - set(GRETEL_TO_SPECIALTY)
  assert not missing, f"unmapped gretelai labels: {missing}"
  assert set(GRETEL_TO_SPECIALTY.values()) <= set(SPECIALTIES)
  ```
  (Repeat for Tulsiandhare if present.)

- [ ] **Step 4: Build unified frame**
  ```python
  import pandas as pd
  rows = [(t, GRETEL_TO_SPECIALTY[d.lower()]) for t, d in
          zip(gret["input_text"], gret["output_text"])]
  if mult is not None:
      rows += [(q, TULSI_TO_SPECIALTY[str(d)]) for q, d in
               zip(mult["patient_query"], mult["disease"]) if str(d) in TULSI_TO_SPECIALTY]
  df = pd.DataFrame(rows, columns=["text","specialty"]).dropna()
  df["text"] = df["text"].str.lower().str.strip()
  print(df["specialty"].value_counts())
  assert df["specialty"].isin(SPECIALTIES).all()
  ```

- [ ] **Step 5: Show a few Hindi/Hinglish rows** mapped to specialty (markdown + a sample print),
  so the multilingual coverage is visible.

- [ ] **Step 6: Commit**

```bash
git add apps/ml-service/notebooks/triage_rnn.ipynb
git commit -m "ml: triage notebook data load + disease->specialty unification"
```

---

### Task 3: Baseline (TF-IDF + LogReg)

**Files:** modify the notebook

- [ ] **Step 1: Split + baseline cell**
  ```python
  from sklearn.model_selection import train_test_split
  from sklearn.feature_extraction.text import TfidfVectorizer
  from sklearn.linear_model import LogisticRegression
  from sklearn.metrics import accuracy_score, f1_score, confusion_matrix
  Xtr, Xte, ytr, yte = train_test_split(df["text"], df["specialty"],
                                        test_size=0.2, stratify=df["specialty"], random_state=SEED)
  tfidf = TfidfVectorizer(ngram_range=(1,2), min_df=2)
  base = LogisticRegression(max_iter=1000)
  base.fit(tfidf.fit_transform(Xtr), ytr)
  pred = base.predict(tfidf.transform(Xte))
  base_acc = accuracy_score(yte, pred); base_f1 = f1_score(yte, pred, average="macro")
  print("baseline acc", base_acc, "macro-F1", base_f1)
  assert base_acc > 0.4  # sanity floor
  ```
- [ ] **Step 2: Plot the confusion matrix** (matplotlib) as a visible artifact for the mentor.
- [ ] **Step 3: Commit**

```bash
git add apps/ml-service/notebooks/triage_rnn.ipynb
git commit -m "ml: triage notebook TF-IDF+LogReg baseline"
```

---

### Task 4: BiLSTM (the showpiece) + comparison

**Files:** modify the notebook

- [ ] **Step 1: Vectorization + model cell** (bake `TextVectorization` into the model so serving
  needs no Keras tokenizer)
  ```python
  import tensorflow as tf
  from tensorflow.keras import layers, Model
  labels = sorted(df["specialty"].unique())
  lab2i = {s:i for i,s in enumerate(labels)}
  ytr_i = np.array([lab2i[y] for y in ytr]); yte_i = np.array([lab2i[y] for y in yte])
  vec = layers.TextVectorization(max_tokens=5000, output_sequence_length=40)
  vec.adapt(Xtr.values)
  inp = layers.Input(shape=(1,), dtype=tf.string)
  x = vec(inp)
  x = layers.Embedding(5000, 64, mask_zero=True)(x)
  x = layers.Bidirectional(layers.LSTM(64))(x)
  x = layers.Dropout(0.3)(x)
  out = layers.Dense(len(labels), activation="softmax")(x)
  model = Model(inp, out)
  model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
  ```
- [ ] **Step 2: Train + curves cell**
  ```python
  es = tf.keras.callbacks.EarlyStopping(patience=4, restore_best_weights=True)
  hist = model.fit(Xtr.values, ytr_i, validation_split=0.15, epochs=40, batch_size=32, callbacks=[es])
  # plot hist.history loss + accuracy (train vs val)
  bilstm_acc = model.evaluate(Xte.values, yte_i, verbose=0)[1]
  print("BiLSTM test acc", bilstm_acc)
  assert bilstm_acc >= base_acc - 0.05  # BiLSTM should be at least competitive
  ```
- [ ] **Step 3: Live predictions cell** — terse + Hinglish sentinels:
  ```python
  for s in ["nausea", "itchy rash on skin", "chest pain", "mujhe bukhar hai", "ghutne me dard"]:
      p = model.predict(np.array([s.lower()]), verbose=0)[0]
      print(s, "->", labels[p.argmax()], round(float(p.max()),3))
  ```
- [ ] **Step 4: Bonus** — gretelai-subset disease-level accuracy (train a quick LogReg on the 22
  disease labels for the gretelai rows only) to show "the model also implies a plausible disease".
- [ ] **Step 5: Commit**

```bash
git add apps/ml-service/notebooks/triage_rnn.ipynb
git commit -m "ml: triage notebook BiLSTM train + curves + comparison"
```

---

### Task 5: Export ONNX + labels + model card

**Files:** modify the notebook; produce artifacts under `artifacts/`

- [ ] **Step 1: Export cell**
  ```python
  import tf2onnx, onnx
  spec = (tf.TensorSpec((None, 1), tf.string, name="symptom"),)
  onnx_model, _ = tf2onnx.convert.from_keras(model, input_signature=spec, opset=15)
  onnx.save(onnx_model, str(ARTIFACTS / "triage_bilstm.onnx"))
  (ARTIFACTS / "specialty_labels.json").write_text(json.dumps(labels))
  ```
  > If `tf2onnx` cannot convert the baked-in `TextVectorization` (a known limitation),
  > fall back: export the Dense/LSTM graph WITHOUT vectorization, write `vocab.json`
  > (`vec.get_vocabulary()`) + `output_sequence_length`, and implement token→id padding in
  > Phase 2's `infer.predict`. Record which path was taken in the model card.
- [ ] **Step 2: Validate the ONNX in-notebook**
  ```python
  import onnxruntime as ort
  sess = ort.InferenceSession(str(ARTIFACTS / "triage_bilstm.onnx"), providers=["CPUExecutionProvider"])
  probs = sess.run(None, {sess.get_inputs()[0].name: np.array([["itchy rash"]], dtype=object)})[0]
  print("onnx ok ->", labels[probs[0].argmax()])
  assert probs.shape[-1] == len(labels)
  ```
- [ ] **Step 3: Write `model_card.md`** into `artifacts/`: datasets + licenses, class list, baseline
  vs BiLSTM metrics, the terse/Hinglish examples, intended use ("suggestion for doctor review,
  routes not diagnoses"), and the synthetic-data caveat.
- [ ] **Step 4: Download the artifacts from Colab and commit them to the repo**
  ```bash
  # locally, after placing the downloaded files:
  git add apps/ml-service/app/triage_model/artifacts/triage_bilstm.onnx \
          apps/ml-service/app/triage_model/artifacts/specialty_labels.json \
          apps/ml-service/app/triage_model/artifacts/model_card.md
  git commit -m "ml: commit trained triage ONNX + labels + model card"
  ```
- [ ] **Step 5: Verify Phase 2 picks them up** — run
  `cd apps/ml-service && ./.venv/Scripts/python.exe -m pytest tests/test_triage_artifacts.py tests/test_triage_pipeline.py -v`.
  Expected: the previously-skipped real-prediction + artifact tests now PASS.

## Self-review notes
- Spec Phase 1 coverage: scaffold+license gate (T1), data+maps (T2), baseline (T3), BiLSTM+
  compare+bonus (T4), ONNX/labels/model-card export + commit + Phase-2 verification (T5). Covered.
- License gate is the first action (T1 Step 1) with a concrete gretelai-only + lexicon fallback.
- ONNX `TextVectorization` risk has a documented fallback (T5 Step 1) consistent with Phase 2's
  `infer.predict` note.
- Column names (`input_text`/`output_text` for gretelai; `patient_query`/`disease` for
  Tulsiandhare) must be confirmed against the live dataset at build time and adjusted if the
  cards differ; the completeness assert (T2 Step 3) will catch a wrong mapping.

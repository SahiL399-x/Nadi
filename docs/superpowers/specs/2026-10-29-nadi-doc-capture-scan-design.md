# NADI — Document Capture & Scan workstream (design)

Date: 2026-10-29
Status: approved design, pending spec review → implementation plan
Related: [OCR Workstream A](2026-10-25-nadi-ml-workstream-a-ocr-design.md); memory `nadi-ml-approach`, `nadi-resume-point`.

## 1. Problem & goal

Today a patient's lab report is captured as a single raw photo: `upload.ts`
resizes to 1600px, compresses to WEBP, and PUTs it to MinIO. Whatever the camera
or gallery hands over goes straight to OCR — blurry, skewed, uncropped photos
included — and PDFs are not accepted at all.

Goal: give report capture a real **"scanner"** experience, like CamScanner /
Microsoft Lens:

- Capture by **camera scan** (auto edge-detection, perspective crop, enhance),
  **gallery** image, or **file** (PDF / image).
- **Multi-page** reports.
- Clean up unclear uploads (contrast/deskew) before OCR.
- Feed the cleaned document into the existing OCR pipeline unchanged.

This improves OCR input quality, which stacks on top of the Step-2 parser
improvements (recognition is already ~80–95%; cleaner input lifts it further).

## 2. Non-goals

- No custom computer-vision edge detection — we use the OS-native scanners.
- No change to the OCR extraction logic (`parse.py` / `normalize.py`) — this
  workstream only changes what *reaches* OCR.
- No OCR of the PDF text layer — PDFs are rasterized and OCR'd as images
  (lab-report PDFs are usually scans without a reliable text layer, and this
  keeps one code path).
- **The doctor-facing report viewer UI is a separate, sequenced spec** (see §10).
  This spec's only obligation to it is to **persist the full extraction** (§5.4)
  and ensure a scan can be fetched for viewing.

## 3. Key decisions (from brainstorm)

| Decision | Choice | Why |
|---|---|---|
| On-device scanner | **`react-native-document-scanner-plugin`** (ML Kit on Android, VisionKit on iOS) via Expo config plugin | Free, production-grade auto-crop/enhance/multi-page/PDF; no custom CV; fits existing dev-build workflow |
| Input types | Camera scan + gallery image + PDF file + multi-page | All requested |
| PDF rasterization lib | **`pypdfium2`** (PDFium, permissive BSD/Apache) | Avoids PyMuPDF's **AGPL-3.0** copyleft — matches NADI's strict-licensing rule |
| Where PDFs rasterize | **Server-side** in `ml-service` (uploaded PDFs only; camera scans emit JPEGs) | Keeps the app simple; one rasterization path |
| Server enhancement | Included, **upload/gallery path only** (not camera — scanner already enhances) | Low cost (OpenCV already a PaddleOCR dep); helps blurry gallery photos |
| Scope | All three phases in one spec | User choice |

## 4. Architecture & data flow

```
Capture sheet
  ├─ Scan  → native scanner (ML Kit/VisionKit) → per-page JPEG(s)  ─┐
  ├─ Gallery → expo-image-picker → image(s)                         ─┤
  └─ File  → expo-document-picker → PDF | image                     ─┤
                                                                    ▼
                               upload.ts  (per file/page)
                 image → resize→WEBP ;  PDF → upload as-is (application/pdf)
                                                                    ▼
                    presigned PUT → MinIO → objectKey[]  (ext reflects type)
                                                                    ▼
          triage intake: reportImageUris[] (EXISTING list loop; one row + one
                         ml_client.document() call per key)
                                                                    ▼
   ml-service document(objectKey):
     preprocess: sniff magic bytes
        · image  → [enhance if flagged] → single image
        · PDF    → pypdfium2 rasterize each page → [enhance] → N images
     pipeline: OCR each image → concat fields → labs/fields/needsReview
```

Crucial reuse: **multi-file already works** — triage intake takes a *list* of
object keys and loops OCR per key (`consultation_service.py:38`). Multi-page is
just multiple keys. Presign is content-type-agnostic (`presign_put` pins only
bucket+key), so PDF upload needs no API change.

## 5. Component changes

### 5.1 Mobile (`apps/mobile`)
- **Dependency:** add `react-native-document-scanner-plugin` + its Expo config
  plugin (camera permission) to `app.json`; new dev build via existing prebuild
  flow. Add `expo-document-picker` (gallery already available via
  `expo-image-picker` or add it).
- **`CaptureSheet` component (new):** action sheet with Scan / Gallery / File.
  - Scan → `scanDocument({ maxNumDocuments, responseType: imageFilePaths })`
    → array of page URIs.
  - Gallery → `expo-image-picker` (images, multiple).
  - File → `expo-document-picker` (`application/pdf`, image/*).
- **`upload.ts`:** branch by type — images keep resize→WEBP; PDFs upload
  verbatim with `content-type: application/pdf`. Return objectKey per item.
- **`useReportUploads`:** already list-based; add a thumbnail review strip
  (reorder/remove/retry) before confirming; expose ordered `objectKeys`.
- Wire the sheet into the triage capture step (replaces the single picker).

### 5.2 Backend (`apps/api`)
- **`uploads.py`:** accept an optional `source` + `ext` hint so the generated
  key encodes **both the type and the capture source** in its path, which is the
  only signal ml-service needs:
  `reports/scan/<uuid>.webp` · `reports/upload/<uuid>.webp` · `reports/upload/<uuid>.pdf`.
  Still server-generated, still presigned; `source` defaults to `upload`. No
  other change. (This avoids adding a field to the frozen `document()` contract.)
- Report model + triage intake loop unchanged.

### 5.3 ml-service (`apps/ml-service`)
- **`preprocess.py`:**
  - `load_and_validate` stays for images; add `load_document(bytes) -> list[image]`
    that sniffs magic bytes: `%PDF` → `pypdfium2` rasterize pages (cap pages,
    e.g. 10) at ~200 DPI; image → `[load_and_validate(bytes)]`.
  - `enhance(image)` (OpenCV): grayscale + CLAHE contrast + deskew; applied only
    when the object key is under `reports/upload/` (gallery/file source); keys
    under `reports/scan/` skip it (the native scanner already enhanced them).
- **`pipeline.py`:** `extract_report` iterates the page list from
  `load_document`, OCRs each, concatenates `fields`; existing single-image path
  is the one-element case. Never-raise fallback preserved.
- **Deps:** add `pypdfium2` (permissive) to `pyproject.toml` + container. OpenCV
  already present via PaddleOCR.

### 5.4 Persist the full extraction (feeds the downstream doctor viewer)
- Today only the numeric "known analyte" subset is stored (`LabValue` per
  report); the richer Step-2 output (qualitative results, LOINC, canonical/raw
  names, `needsReview`, per-field `qualityFlags`) is discarded after triage.
- **Add an `extraction_json` (JSON/text) column to `Report`** and persist the
  full `fields` + `needsReview` + `modelVersion` there at intake. `LabValue`
  rows stay (back-compat). `ml_client.document()` must return the full result
  (currently returns only `["labs"]`). Migration is additive.
- This makes the doctor viewer a pure read+UI feature with no extraction rework.

## 6. Phased build order (single spec, incremental delivery)

1. **Phase 1 — Scanner + gallery, multi-page images.** Mobile only; reuses the
   whole pipeline; zero ml-service change. Delivers the CamScanner UX.
2. **Phase 2 — PDF.** ml-service `pypdfium2` rasterization + multi-page OCR;
   `upload.ts` PDF branch; api key-extension hint.
3. **Phase 3 — Server-side enhancement** for the gallery/upload path.

## 7. Testing

- **Mobile:** unit-test `upload.ts` type branching (image vs PDF content-type);
  mock the scanner plugin; `useReportUploads` multi-item ordering/retry.
- **ml-service (TDD):** `load_document` sniffs PDF vs image; rasterizes a tiny
  fixture PDF to N images; page cap enforced; `enhance` returns a valid image;
  `extract_report` concatenates fields across pages; non-PDF path byte-identical
  to today. Fallback still never raises.
- **api:** `sign` returns a key with the requested extension.

## 8. Risks & mitigations

- **Native module needs a dev build** — already standard here (LiveKit/MapLibre).
  Physical-device gate for the demo.
- **Scanner UX differs iOS vs Android** (VisionKit vs ML Kit) — acceptable; both
  are high quality. Document in the verification script.
- **Large/odd PDFs** — cap pages + DPI; `load_document` failures fall through to
  the existing never-raise `_safe_result`.
- **Licensing** — scanner (ML Kit/VisionKit, Apache-2.0/system) and `pypdfium2`
  (BSD/Apache) are permissive; **PyMuPDF (AGPL) explicitly avoided**.

## 9. Open questions

None blocking. Revisit page cap (default 10) and enhancement aggressiveness
after first real-device testing.

## 10. Downstream: Doctor report viewer (separate spec, sequenced next)

Not built here — recorded so the pipeline above feeds it correctly. To be its
own `*-doctor-report-viewer-design.md` spec after this workstream.

- **Goal:** in the doctor's patient-reports section, show each report the patient
  uploaded as a **scanned preview**, with the field extraction laid out cleanly
  beneath, "sleek modern."
- **UI pattern (user-specified, ref: Google Classroom attachment card):**
  - Each report = a **rectangular preview card** — label/filename on the left, a
    **scan thumbnail on the right**; tap → full-screen scan view.
  - Extracted fields rendered **compactly, one per line**, with a **dropdown /
    expand arrow** to reveal the *full* extraction aggregated across all of the
    patient's uploaded reports.
  - Report preview cards listed below the extraction summary.
- **Backend prerequisites (new in the viewer spec):**
  - `presign_get(object_key)` + a doctor endpoint returning, per patient report:
    `{ objectKey, imageUrl (presigned GET), extraction_json, labValues[] }`.
    RBAC: doctor must be on the patient's consultation (reuse existing guards).
  - Reads `Report.extraction_json` persisted by §5.4 (why that hook exists here).
- **Depends on:** this capture/scan workstream (scanned reports + persisted
  extraction) being in place first.

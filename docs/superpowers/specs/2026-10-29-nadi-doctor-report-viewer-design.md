# NADI — Doctor Report Viewer (design)

Date: 2026-10-29
Status: approved design, pending spec review → implementation plan
Depends on: Document Capture & Scan workstream (merged `033d87d`) — `Report.extraction_json` now persists the full OCR extraction per report. Recorded as §10 of `2026-10-29-nadi-doc-capture-scan-design.md`.

## 1. Problem & goal

When a doctor opens a patient, they can't see the lab reports the patient uploaded, nor the extracted values. The existing doctor `lab-reports.tsx` is a flat list (patient name / date / status) with no scans and no data.

Goal: in the doctor's **Patient File**, add a **Reports** section that shows, for the selected patient:
- the field extraction **compactly** (abnormal values first), with a dropdown to **expand the full extraction aggregated across all the patient's reports**;
- each uploaded report as a **rectangular preview card** (label + date + scan thumbnail); tap → **full-screen scan**.

This is purely **read + display** — it rides on data already persisted (`Report.extraction_json`); no changes to capture or OCR.

## 2. Non-goals

- No change to capture/OCR/extraction (`parse.py`, `normalize.py`, the capture flow).
- No editing/annotating of extracted values by the doctor (future).
- Not patient-facing (patients already see their own reports list).
- No PDF rendering in-app — PDF reports open externally (see §5.1).

## 3. Key decisions (from brainstorm)

| Decision | Choice |
|---|---|
| Placement | A **Reports section inside the Patient File** (`patient/[pid].tsx`), reusing the `owned_by_doctor` RBAC guard |
| Compact view | **Abnormal values first** (flag `L`/`H`), then a `+N more` dropdown → full extraction grouped by report |
| Data source | **`Report.extraction_json`** (authoritative). The `LabValue` table is NOT populated at intake today — do not read it. |
| Report date | Use the **consultation's `created_at`** (the `Report` model has no timestamp — avoids a migration) |
| PDF reports | Show a **"PDF" placeholder card**; tap opens the PDF externally. Image/scan reports show a real thumbnail |
| needsReview | Per-report **"Needs review"** badge from `extraction_json.needsReview` |
| Scope | Read-only; its own spec→plan→build cycle |

## 4. Architecture & data flow

```
Patient File (patient/[pid].tsx)
  └─ ReportsSection(patientId)
       useReportFile(patientId)  ──GET /v1/doctor/patients/{pid}/reports──▶
                                                                            │
   api: require_role("doctor") + owned_by_doctor(pid, doctor)              │
        query Report JOIN Consultation                                     │
          WHERE Consultation.patient_id = pid AND doctor_id = this doctor  │
        for each report: parse extraction_json, presign_get(object_key)    │
       ◀── list[ReportViewOut] { reportId, kind, imageUrl, date,           │
                                 needsReview, extracted, fields[] }         ┘
  Frontend aggregates fields across reports → abnormal-first compact view
  Renders: compact + expand-all, then ReportCard[] (thumbnail | PDF),
           tap card → ScanViewer (full-screen, zoom)
```

## 5. Components

### 5.1 Frontend (`apps/mobile`)
- **`useReportFile(patientId)`** (`src/features/doctor/useReportFile.ts`) — React Query hook → `GET /v1/doctor/patients/{pid}/reports`, `refetchOnWindowFocus`/on screen focus (presigned URLs are short-lived). Zod schema in `src/api/doctorPortal.ts`.
- **`src/features/doctor/reportAggregate.ts`** — pure helpers (unit-tested):
  - `abnormalFirst(reports): Field[]` — flatten all reports' `fields`, order `L`/`H` first, then the rest; dedupe is NOT required (same analyte across reports = legitimate repeats over time).
  - `isAbnormal(field): boolean` — `field.flag === 'L' || field.flag === 'H'`.
- **`ReportsSection`** (`src/components/doctor/ReportsSection.tsx`) — owns compact/expanded state; renders the compact abnormal list + `+N more` toggle (expanded = full extraction grouped by report), then the `ReportCard` list. Empty state "No reports uploaded yet."
- **`ReportCard`** (`src/components/doctor/ReportCard.tsx`) — rectangular card: label ("Lab report N") + date on the left; right side = `<Image source={{uri: imageUrl}}>` for `kind:'image'`, or a "PDF" placeholder for `kind:'pdf'`. "Needs review" badge when flagged. Tap → image reports open `ScanViewer`; PDF reports open the URL via `expo-web-browser`.
- **`ScanViewer`** (`src/components/doctor/ScanViewer.tsx`) — full-screen modal, pinch-zoomable image of `imageUrl`.
- Wire `<ReportsSection patientId={pid} />` into `patient/[pid].tsx` after the existing sections.
- **Demo gotcha (carry forward):** on device, `S3_ENDPOINT` must be the laptop's LAN IP so phones can fetch presigned GET URLs (same constraint as report upload).

### 5.2 Backend (`apps/api`)
- **`storage_service.presign_get(object_key) -> str`** — mirrors `presign_put` with `get_object`, `ExpiresIn=300`.
- **`ReportViewOut`** schema (new `app/schemas/report_view.py`):
  `reportId: str`, `kind: Literal['image','pdf']`, `imageUrl: str`, `date: str`, `needsReview: bool`, `extracted: bool`, `fields: list[dict]`.
  (`fields` is the authoritative richer list from `extraction_json["fields"]`; the back-compat `labs` subset is intentionally NOT returned — `fields` carries every value plus the `flag`, so the UI needs only `fields`.)
- **`report_view_service.list_for_patient(db, doctor_id, patient_id) -> list[ReportViewOut]`**:
  - query `Report` JOIN `Consultation` WHERE `Consultation.patient_id == patient_id AND Consultation.doctor_id == doctor_id`, ordered by `Consultation.created_at`.
  - per report: `kind` = `'pdf' if object_key.endswith('.pdf') else 'image'`; `imageUrl = presign_get(object_key)`; parse `extraction_json` (null/malformed → `extracted=False`, empty `fields`, `needsReview=False`); `date` from the consultation's `created_at`.
- **`GET /v1/doctor/patients/{patient_id}/reports`** in `doctor_portal.py`:
  `require_role("doctor")`; if not `patient_service.owned_by_doctor(db, patient_id, user.id)` → 404; else return the service list.

## 6. Edge cases
- No reports for the patient → empty list → "No reports uploaded yet."
- `extraction_json` null (legacy report, or OCR was off at intake) → card shows the scan with "Not yet extracted" instead of fields (`extracted: false`).
- PDF report → placeholder card, opens externally (no in-app render).
- Presigned URL expiry → short TTL; refetch on screen focus.
- Doctor doesn't own the patient → 404 (no enumeration).
- Malformed `extraction_json` → treat as not-extracted (never 500 the whole file).

## 7. Testing
- **api:**
  - returns per-report `{kind,imageUrl,fields,needsReview,extracted}` for a patient the doctor owns (monkeypatch `presign_get`);
  - 404 for a patient the doctor does NOT own (RBAC);
  - a report with null `extraction_json` → `extracted: false`, empty fields;
  - `kind` is `pdf` for a `.pdf` key, `image` otherwise;
  - `presign_get` returns a URL (shape).
- **mobile:**
  - `abnormalFirst` orders `L`/`H` fields before normal, counts correctly;
  - `isAbnormal` truth table;
  - `ReportCard` renders an `<Image>` for `kind:'image'` and the placeholder for `kind:'pdf'`.

## 8. Risks & mitigations
- **Empty `LabValue` trap:** the obvious-looking `LabValue` table is unused; reading it would show nothing. Mitigation: this spec mandates `extraction_json` as the source (§3), and the api test asserts fields come through.
- **Presigned URL on device:** needs the LAN `S3_ENDPOINT` for the demo (documented).
- **Large extraction:** a report can have many fields; the compact view caps visible abnormals and hides the rest behind the dropdown, so the file screen stays light.

## 9. Open questions
None blocking. Revisit whether to add a `created_at` to `Report` if per-report (not per-consultation) timestamps become important.

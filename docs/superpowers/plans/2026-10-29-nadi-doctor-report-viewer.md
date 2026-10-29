# Doctor Report Viewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Reports section to the doctor's Patient File that shows each uploaded report as a scan-preview card plus the field extraction (abnormal-first, with expand-all across the patient's reports).

**Architecture:** A new doctor endpoint returns, per report the doctor owns for a patient, the presigned scan URL + parsed `extraction_json`. The mobile Patient File renders a `ReportsSection` that aggregates the fields abnormal-first (compact + expand), lists scan-preview cards, and opens a full-screen scan (image) or external browser (PDF). Read-only; no capture/OCR changes.

**Tech Stack:** FastAPI + SQLAlchemy (Python), boto3/MinIO presigned GET, Expo/React Native + TypeScript + Zod + React Query.

## Global Constraints

- **Data source is `Report.extraction_json`** (parsed JSON). Do NOT read the `LabValue` table — it is not populated at intake and would show nothing. (spec §3, §8)
- RBAC: reuse `patient_service.owned_by_doctor(db, patient_id, doctor_id)`; a patient the doctor doesn't own → **404** (no enumeration). (spec §5.2)
- `presign_get` TTL = **300s**, mirrors `presign_put`. (spec §5.2)
- `kind` = `'pdf'` if `object_key` ends `.pdf`, else `'image'`. (spec §5.2)
- Report date = the **consultation's `created_at`** (the `Report` model has no timestamp — no migration). (spec §3)
- Null/malformed `extraction_json` → `extracted: false`, empty `fields`, `needsReview: false` (never 500). (spec §6)
- Compact view shows **abnormal (`flag` `L`/`H`) fields first**; expand reveals the rest. (spec §3)
- `fields` is the only extraction payload returned (NOT `labs`). (spec §5.2)
- No AI attribution in commits (project rule). Work on a feature branch (not `main`).
- api tests: `cd apps/api && ./.venv/Scripts/python.exe -m pytest`. mobile: `cd apps/mobile && npm test` + `npx tsc --noEmit`.
- Mobile UI: import UI components by DIRECT path (e.g. `@/components/ui/Card`), never the `@/components/ui` barrel (jest/reanimated crash).

---

### Task 1: Backend — `GET /v1/doctor/patients/{patient_id}/reports` + `presign_get`

**Files:**
- Modify: `apps/api/app/services/storage_service.py` (add `presign_get`)
- Create: `apps/api/app/schemas/report_view.py`
- Create: `apps/api/app/services/report_view_service.py`
- Modify: `apps/api/app/routers/doctor_portal.py` (add endpoint + imports)
- Test: `apps/api/tests/test_report_view.py`

**Interfaces:**
- Consumes: `patient_service.owned_by_doctor(db, patient_id, doctor_id) -> bool`; models `Report` (`id, consultation_id, object_key, extraction_json`) and `Consultation` (`id, patient_id, doctor_id, created_at`).
- Produces: `GET /v1/doctor/patients/{patient_id}/reports` → `list[ReportViewOut]` where `ReportViewOut = { reportId: str, kind: 'image'|'pdf', imageUrl: str, date: str, needsReview: bool, extracted: bool, fields: list[dict] }`. Service `report_view_service.list_for_patient(db, doctor_id, patient_id) -> list[ReportViewOut]`. `storage_service.presign_get(object_key) -> str`.

- [ ] **Step 1: Write the failing tests**

```python
# apps/api/tests/test_report_view.py
import json
import uuid

from app.models import Consultation, ConsultationStatus, Patient, Report, Role, User
import app.services.storage_service as storage_service


def _doctor_token(client, db):
    phone = f"+91{uuid.uuid4().int % 10**10:010d}"
    db.add(User(id=uuid.uuid4(), phone=phone, role=Role.doctor, name="Dr R"))
    db.commit()
    client.post("/v1/auth/request-otp", json={"phone": phone})
    r = client.post("/v1/auth/verify-otp", json={"phone": phone, "code": "123456"})
    return r.json()["accessToken"], r.json()["userId"]


def _patient_with_report(db, doctor_id, object_key, extraction_json):
    pid = uuid.uuid4()
    db.add(User(id=pid, phone=f"+91{uuid.uuid4().int % 10**10:010d}", role=Role.patient, name="P"))
    db.flush()
    db.add(Patient(user_id=pid, age=30, sex="F"))
    cid = uuid.uuid4()
    db.add(Consultation(id=cid, patient_id=pid, doctor_id=doctor_id,
                        status=ConsultationStatus.BOOKED, symptom_text_raw="x"))
    db.flush()
    db.add(Report(id=uuid.uuid4(), consultation_id=cid, object_key=object_key,
                  ocr_status="done", extraction_json=extraction_json))
    db.commit()
    return str(pid)


def test_reports_returns_extraction_for_owned_patient(client, db, monkeypatch):
    monkeypatch.setattr(storage_service, "presign_get", lambda key: f"http://minio/{key}?sig=x")
    token, doctor_id = _doctor_token(client, db)
    extraction = json.dumps({"fields": [{"testNameNormalized": "Haemoglobin", "flag": "L"}],
                             "needsReview": True})
    pid = _patient_with_report(db, doctor_id, "reports/upload/u/a.webp", extraction)
    r = client.get(f"/v1/doctor/patients/{pid}/reports", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["kind"] == "image"
    assert body[0]["imageUrl"].startswith("http")
    assert body[0]["extracted"] is True
    assert body[0]["needsReview"] is True
    assert body[0]["fields"][0]["testNameNormalized"] == "Haemoglobin"


def test_reports_404_for_unowned_patient(client, db, monkeypatch):
    monkeypatch.setattr(storage_service, "presign_get", lambda key: "x")
    token, _ = _doctor_token(client, db)
    other_doctor = uuid.uuid4()
    db.add(User(id=other_doctor, phone=f"+91{uuid.uuid4().int % 10**10:010d}", role=Role.doctor, name="Other"))
    db.commit()
    pid = _patient_with_report(db, other_doctor, "reports/upload/u/b.webp", "{}")
    r = client.get(f"/v1/doctor/patients/{pid}/reports", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


def test_reports_pdf_kind_and_null_extraction(client, db, monkeypatch):
    monkeypatch.setattr(storage_service, "presign_get", lambda key: f"http://minio/{key}")
    token, doctor_id = _doctor_token(client, db)
    pid = _patient_with_report(db, doctor_id, "reports/upload/u/c.pdf", None)
    r = client.get(f"/v1/doctor/patients/{pid}/reports", headers={"Authorization": f"Bearer {token}"})
    body = r.json()
    assert body[0]["kind"] == "pdf"
    assert body[0]["extracted"] is False
    assert body[0]["fields"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/test_report_view.py -v`
Expected: FAIL (404 route / `presign_get` missing).

- [ ] **Step 3: Add `presign_get` to storage_service**

```python
# apps/api/app/services/storage_service.py  — add after presign_put
def presign_get(object_key: str) -> str:
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": object_key},
        ExpiresIn=300,
    )
```

- [ ] **Step 4: Create the schema**

```python
# apps/api/app/schemas/report_view.py
from typing import Literal

from pydantic import BaseModel


class ReportViewOut(BaseModel):
    reportId: str
    kind: Literal["image", "pdf"]
    imageUrl: str
    date: str
    needsReview: bool
    extracted: bool
    fields: list[dict]
```

- [ ] **Step 5: Create the service**

```python
# apps/api/app/services/report_view_service.py
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Consultation, Report
from app.schemas.report_view import ReportViewOut
from app.services import storage_service


def _parse(extraction_json: str | None) -> tuple[bool, list[dict], bool]:
    """(extracted, fields, needsReview). Null/malformed -> (False, [], False)."""
    if not extraction_json:
        return False, [], False
    try:
        data = json.loads(extraction_json)
    except (ValueError, TypeError):
        return False, [], False
    return True, list(data.get("fields", [])), bool(data.get("needsReview", False))


def list_for_patient(db: Session, doctor_id, patient_id) -> list[ReportViewOut]:
    rows = db.execute(
        select(Report, Consultation)
        .join(Consultation, Consultation.id == Report.consultation_id)
        .where(Consultation.patient_id == patient_id)
        .where(Consultation.doctor_id == doctor_id)
        .order_by(Consultation.created_at)
    ).all()
    out: list[ReportViewOut] = []
    for report, consult in rows:
        extracted, fields, needs_review = _parse(report.extraction_json)
        out.append(
            ReportViewOut(
                reportId=str(report.id),
                kind="pdf" if report.object_key.endswith(".pdf") else "image",
                imageUrl=storage_service.presign_get(report.object_key),
                date=consult.created_at.strftime("%d %b %Y") if consult.created_at else "",
                needsReview=needs_review,
                extracted=extracted,
                fields=fields,
            )
        )
    return out
```

- [ ] **Step 6: Add the endpoint**

```python
# apps/api/app/routers/doctor_portal.py
# add to the schema imports:
from app.schemas.report_view import ReportViewOut
# add to the services import list (the `from app.services import (...)` block):
#     report_view_service,

# add this route (e.g. right after patient_profile):
@router.get("/patients/{patient_id}/reports", response_model=list[ReportViewOut])
def patient_reports(
    patient_id: str,
    user: User = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
):
    if not patient_service.owned_by_doctor(db, patient_id, user.id):
        raise HTTPException(status_code=404, detail="not found")
    return report_view_service.list_for_patient(db, user.id, patient_id)
```

- [ ] **Step 7: Run tests + full api suite, commit**

Run: `cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/test_report_view.py -v && ./.venv/Scripts/python.exe -m pytest -q`
Expected: new tests PASS; full suite PASS.

```bash
git add apps/api/app/services/storage_service.py apps/api/app/schemas/report_view.py apps/api/app/services/report_view_service.py apps/api/app/routers/doctor_portal.py apps/api/tests/test_report_view.py
git commit -m "api: doctor per-patient reports endpoint with presigned scans + parsed extraction"
```

---

### Task 2: Frontend data layer — schema, client, hook, abnormal-first aggregation

**Files:**
- Modify: `apps/mobile/src/api/doctorPortal.ts` (add `ExtractionFieldSchema`, `ReportViewSchema`, `getReportFile`)
- Create: `apps/mobile/src/features/doctor/useReportFile.ts`
- Create: `apps/mobile/src/features/doctor/reportAggregate.ts`
- Test: `apps/mobile/src/features/doctor/__tests__/reportAggregate.test.ts`

**Interfaces:**
- Consumes: `GET /v1/doctor/patients/{id}/reports` (Task 1) → array of `{reportId, kind, imageUrl, date, needsReview, extracted, fields}`.
- Produces: `ReportView`, `ExtractionField` types; `getReportFile(patientId): Promise<ReportView[]>`; `useReportFile(patientId)` (React Query); `isAbnormal(f): boolean` (`flag` is `L`/`H`); `abnormalFirst(reports: ReportView[]): ExtractionField[]`.

- [ ] **Step 1: Write the failing tests**

```ts
// apps/mobile/src/features/doctor/__tests__/reportAggregate.test.ts
import { abnormalFirst, isAbnormal } from '@/features/doctor/reportAggregate';

const field = (name: string, flag?: string) => ({ testNameNormalized: name, flag });
const report = (fields: any[]) =>
  ({ reportId: 'r', kind: 'image', imageUrl: '', date: '', needsReview: false, extracted: true, fields } as any);

test('isAbnormal is true only for L or H', () => {
  expect(isAbnormal(field('x', 'L'))).toBe(true);
  expect(isAbnormal(field('x', 'H'))).toBe(true);
  expect(isAbnormal(field('x', 'N'))).toBe(false);
  expect(isAbnormal(field('x'))).toBe(false);
});

test('abnormalFirst orders flagged fields before normal, across reports', () => {
  const out = abnormalFirst([
    report([field('Normal1', 'N'), field('Low1', 'L')]),
    report([field('High1', 'H'), field('Normal2')]),
  ]);
  expect(out.slice(0, 2).map((f) => f.testNameNormalized)).toEqual(['Low1', 'High1']);
  expect(out).toHaveLength(4);
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/mobile && npm test -- reportAggregate.test.ts`
Expected: FAIL (`reportAggregate` not found).

- [ ] **Step 3: Add schema + client to doctorPortal.ts**

```ts
// apps/mobile/src/api/doctorPortal.ts  — add near the other schemas
export const ExtractionFieldSchema = z
  .object({
    testNameNormalized: z.string().optional(),
    testNameRaw: z.string().optional(),
    valueRaw: z.string().optional(),
    valueNumeric: z.number().nullable().optional(),
    unit: z.string().optional(),
    flag: z.string().optional(),
    loinc: z.string().optional(),
  })
  .passthrough();
export const ReportViewSchema = z.object({
  reportId: z.string(),
  kind: z.enum(['image', 'pdf']),
  imageUrl: z.string(),
  date: z.string(),
  needsReview: z.boolean(),
  extracted: z.boolean(),
  fields: z.array(ExtractionFieldSchema),
});
export type ExtractionField = z.infer<typeof ExtractionFieldSchema>;
export type ReportView = z.infer<typeof ReportViewSchema>;

export const getReportFile = (patientId: string): Promise<ReportView[]> =>
  api.get(`/v1/doctor/patients/${patientId}/reports`, z.array(ReportViewSchema));
```

- [ ] **Step 4: Create the aggregation helpers**

```ts
// apps/mobile/src/features/doctor/reportAggregate.ts
import type { ExtractionField, ReportView } from '@/api/doctorPortal';

export function isAbnormal(f: ExtractionField): boolean {
  return f.flag === 'L' || f.flag === 'H';
}

export function abnormalFirst(reports: ReportView[]): ExtractionField[] {
  const all = reports.flatMap((r) => r.fields);
  return [...all.filter(isAbnormal), ...all.filter((f) => !isAbnormal(f))];
}
```

- [ ] **Step 5: Create the hook**

```ts
// apps/mobile/src/features/doctor/useReportFile.ts
import { useQuery } from '@tanstack/react-query';
import { getReportFile } from '@/api/doctorPortal';

export function useReportFile(patientId: string) {
  return useQuery({ queryKey: ['reportFile', patientId], queryFn: () => getReportFile(patientId) });
}
```

- [ ] **Step 6: Run tests + typecheck, commit**

Run: `cd apps/mobile && npm test -- reportAggregate.test.ts && npx tsc --noEmit`
Expected: PASS, tsc clean.

```bash
git add apps/mobile/src/api/doctorPortal.ts apps/mobile/src/features/doctor/useReportFile.ts apps/mobile/src/features/doctor/reportAggregate.ts apps/mobile/src/features/doctor/__tests__/reportAggregate.test.ts
git commit -m "mobile: doctor report-file data layer (schema, client, hook, abnormal-first aggregation)"
```

---

### Task 3: Frontend UI — ReportCard, ScanViewer, ReportsSection wired into the Patient File

**Files:**
- Create: `apps/mobile/src/components/doctor/ReportCard.tsx`
- Create: `apps/mobile/src/components/doctor/ScanViewer.tsx`
- Create: `apps/mobile/src/components/doctor/ReportsSection.tsx`
- Modify: `apps/mobile/app/(doctor)/patient/[pid].tsx` (add the section)
- Test: `apps/mobile/src/components/doctor/__tests__/ReportCard.test.tsx`

**Interfaces:**
- Consumes: `useReportFile`, `abnormalFirst` (Task 2); `ReportView` type; `Card`/`Skeleton` (direct paths); `expo-web-browser`.
- Produces: `<ReportsSection patientId={string} />` rendered in the Patient File; `<ReportCard report label onOpen />`; `<ScanViewer uri visible onClose />`.

- [ ] **Step 1: Write the failing test (ReportCard image vs PDF branch)**

```tsx
// apps/mobile/src/components/doctor/__tests__/ReportCard.test.tsx
import { render } from '@testing-library/react-native';
import { ReportCard } from '@/components/doctor/ReportCard';

const base = { reportId: '1', imageUrl: 'http://x/y.webp', date: '29 Oct 2026',
  needsReview: false, extracted: true, fields: [] };

test('renders an image thumbnail for image kind', () => {
  const { getByTestId, queryByTestId } = render(
    <ReportCard report={{ ...base, kind: 'image' } as any} label="Lab report 1" onOpen={() => {}} />);
  expect(getByTestId('report-thumb')).toBeTruthy();
  expect(queryByTestId('report-pdf')).toBeNull();
});

test('renders a PDF placeholder for pdf kind', () => {
  const { getByTestId } = render(
    <ReportCard report={{ ...base, kind: 'pdf' } as any} label="Lab report 1" onOpen={() => {}} />);
  expect(getByTestId('report-pdf')).toBeTruthy();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/mobile && npm test -- ReportCard.test.tsx`
Expected: FAIL (`ReportCard` not found).

- [ ] **Step 3: Create ReportCard**

```tsx
// apps/mobile/src/components/doctor/ReportCard.tsx
import { Image, Pressable, Text, View } from 'react-native';
import type { ReportView } from '@/api/doctorPortal';
import { colors, radii, spacing, type as t } from '@/theme/tokens';

export function ReportCard({ report, label, onOpen }: { report: ReportView; label: string; onOpen: () => void }) {
  return (
    <Pressable
      onPress={onOpen}
      style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.md, backgroundColor: colors.surface,
        borderRadius: radii.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.md }}
    >
      <View style={{ flex: 1 }}>
        <Text style={{ fontSize: t.body, fontWeight: '700', color: colors.text }}>{label}</Text>
        <Text style={{ fontSize: t.xs, color: colors.textMuted }}>{report.date}</Text>
        {report.needsReview ? (
          <Text style={{ fontSize: t.xs, color: colors.emergency, fontWeight: '700' }}>Needs review</Text>
        ) : null}
      </View>
      {report.kind === 'image' ? (
        <Image testID="report-thumb" source={{ uri: report.imageUrl }}
          style={{ width: 64, height: 80, borderRadius: radii.sm }} />
      ) : (
        <View testID="report-pdf" style={{ width: 64, height: 80, borderRadius: radii.sm,
          backgroundColor: colors.greenTint, alignItems: 'center', justifyContent: 'center' }}>
          <Text style={{ fontWeight: '800', color: colors.text }}>PDF</Text>
        </View>
      )}
    </Pressable>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/mobile && npm test -- ReportCard.test.tsx`
Expected: PASS.

- [ ] **Step 5: Create ScanViewer**

```tsx
// apps/mobile/src/components/doctor/ScanViewer.tsx
import { Image, Modal, Pressable, ScrollView, useWindowDimensions } from 'react-native';

export function ScanViewer({ uri, visible, onClose }: { uri: string; visible: boolean; onClose: () => void }) {
  const { width, height } = useWindowDimensions();
  return (
    <Modal visible={visible} onRequestClose={onClose} animationType="fade">
      <Pressable onPress={onClose} style={{ flex: 1, backgroundColor: '#000' }}>
        <ScrollView maximumZoomScale={4} minimumZoomScale={1} centerContent
          contentContainerStyle={{ width, height, alignItems: 'center', justifyContent: 'center' }}>
          <Image source={{ uri }} style={{ width, height }} resizeMode="contain" />
        </ScrollView>
      </Pressable>
    </Modal>
  );
}
```

- [ ] **Step 6: Create ReportsSection**

```tsx
// apps/mobile/src/components/doctor/ReportsSection.tsx
import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import * as WebBrowser from 'expo-web-browser';
import { Card } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import { ReportCard } from '@/components/doctor/ReportCard';
import { ScanViewer } from '@/components/doctor/ScanViewer';
import { useReportFile } from '@/features/doctor/useReportFile';
import { abnormalFirst, isAbnormal } from '@/features/doctor/reportAggregate';
import type { ExtractionField, ReportView } from '@/api/doctorPortal';
import { colors, spacing, type as t } from '@/theme/tokens';

const COMPACT_LIMIT = 4;
const flagLabel = (flag?: string) => (flag === 'L' ? '↓ Low' : flag === 'H' ? '↑ High' : '');
const fieldLine = (f: ExtractionField) =>
  `${f.testNameNormalized || f.testNameRaw || 'Result'} ${f.valueRaw ?? ''}${f.unit ? ` ${f.unit}` : ''} ${flagLabel(f.flag)}`.trim();

export function ReportsSection({ patientId }: { patientId: string }) {
  const { data, isLoading } = useReportFile(patientId);
  const [expanded, setExpanded] = useState(false);
  const [viewerUri, setViewerUri] = useState<string | null>(null);

  if (isLoading) return <Skeleton height={100} />;
  const reports = data ?? [];
  if (reports.length === 0) {
    return (
      <Card>
        <Text style={{ fontSize: t.sm, color: colors.textMuted, marginBottom: spacing.xs }}>Reports</Text>
        <Text style={{ fontSize: t.sm, color: colors.text }}>No reports uploaded yet.</Text>
      </Card>
    );
  }

  const ordered = abnormalFirst(reports);
  const visible = expanded ? ordered : ordered.slice(0, COMPACT_LIMIT);
  const open = (r: ReportView) => {
    if (r.kind === 'pdf') void WebBrowser.openBrowserAsync(r.imageUrl);
    else setViewerUri(r.imageUrl);
  };

  return (
    <Card>
      <Text style={{ fontSize: t.sm, color: colors.textMuted, marginBottom: spacing.xs }}>Reports & extraction</Text>
      {visible.map((f, i) => (
        <Text key={i} style={{ fontSize: t.sm, fontWeight: isAbnormal(f) ? '700' : '400',
          color: isAbnormal(f) ? colors.emergency : colors.text }}>
          {fieldLine(f)}
        </Text>
      ))}
      {ordered.length > COMPACT_LIMIT ? (
        <Pressable onPress={() => setExpanded((e) => !e)}>
          <Text style={{ fontSize: t.sm, color: colors.navy, fontWeight: '700', marginTop: spacing.xs }}>
            {expanded ? '▴ Show less' : `▾ +${ordered.length - COMPACT_LIMIT} more results`}
          </Text>
        </Pressable>
      ) : null}
      <View style={{ height: spacing.md }} />
      {reports.map((r, i) => (
        <View key={r.reportId} style={{ marginBottom: spacing.sm }}>
          <ReportCard report={r} label={`Lab report ${i + 1}`} onOpen={() => open(r)} />
        </View>
      ))}
      <ScanViewer uri={viewerUri ?? ''} visible={viewerUri !== null} onClose={() => setViewerUri(null)} />
    </Card>
  );
}
```

- [ ] **Step 7: Wire into the Patient File**

```tsx
// apps/mobile/app/(doctor)/patient/[pid].tsx
// add import:
import { ReportsSection } from '@/components/doctor/ReportsSection';
// add just before the closing </ScrollView>, after the "Past prescriptions" Section:
      <ReportsSection patientId={pid!} />
```

- [ ] **Step 8: Run tests + typecheck, commit**

Run: `cd apps/mobile && npm test -- ReportCard.test.tsx && npx tsc --noEmit`
Expected: PASS, tsc clean.

```bash
git add apps/mobile/src/components/doctor/ReportCard.tsx apps/mobile/src/components/doctor/ScanViewer.tsx apps/mobile/src/components/doctor/ReportsSection.tsx apps/mobile/app/(doctor)/patient/[pid].tsx apps/mobile/src/components/doctor/__tests__/ReportCard.test.tsx
git commit -m "mobile: doctor Reports section with scan-preview cards and expandable extraction"
```

---

## Final verification (after all tasks)

- [ ] `cd apps/api && ./.venv/Scripts/python.exe -m pytest` — all green.
- [ ] `cd apps/mobile && npm test && npx tsc --noEmit` — all green.
- [ ] (Optional device/dev-run) Open a doctor → a patient with uploaded reports → the Reports section shows abnormal-first extraction, expand-all works, image reports open full-screen, PDF reports open externally, "Needs review" badge appears when flagged.

## Spec coverage map

- §5.2 presign_get + endpoint + RBAC + ReportViewOut + service → Task 1
- §5.1 useReportFile + reportAggregate (abnormalFirst/isAbnormal) → Task 2
- §5.1 ReportsSection + ReportCard + ScanViewer + Patient File wiring → Task 3
- §6 edge cases (no reports, null extraction, PDF, needs-review) → Task 1 (null/PDF) + Task 3 (empty state, PDF open, badge)
- §7 testing → Task 1 (api), Task 2 (aggregation), Task 3 (ReportCard)

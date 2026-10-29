# Document Capture & Scan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let patients capture lab reports via a native document scanner, gallery, or PDF/file (multi-page), feed the cleaned document through the existing OCR pipeline, and persist the full extraction per report.

**Architecture:** A new capture sheet in the Expo/RN app offers Scan (native ML Kit/VisionKit via `react-native-document-scanner-plugin`), Gallery (`expo-image-picker`), and File (`expo-document-picker`). The capture *source* is encoded in the presigned object key (`reports/scan/...` vs `reports/upload/...`). ml-service gains PDF→image rasterization (`pypdfium2`) and OpenCV enhancement (upload path only); the existing multi-file triage loop is reused unchanged. The full OCR result is persisted on `Report.extraction_json` to feed the later doctor-viewer spec.

**Tech Stack:** Expo/React Native (TypeScript), FastAPI + SQLAlchemy + Alembic (Python 3.11/3.13), PaddleOCR, Pillow, OpenCV, pypdfium2, boto3/MinIO.

## Global Constraints

- PDF rasterization MUST use **`pypdfium2`** (permissive). **Never PyMuPDF** (AGPL-3.0). (spec §3)
- On-device scanner MUST be **`react-native-document-scanner-plugin`** (ML Kit Android / VisionKit iOS). No custom CV. (spec §3)
- OCR extraction logic (`parse.py`, `normalize.py`) MUST NOT change — only what *reaches* OCR. (spec §2)
- Real OCR stays behind `ML_OCR_ENABLED` (default **OFF**); capture/upload works regardless. (existing)
- Capture source encoded in the object-key prefix: `reports/scan/<userId>/<uuid>.<ext>` or `reports/upload/<userId>/<uuid>.<ext>`. (spec §5.2)
- Enhancement applies **only** to keys containing `/upload/` (scans are pre-enhanced). (spec §5.3)
- PDF rasterization: cap at **10 pages**, render at **~200 DPI**. (spec §8)
- Reuse the existing multi-file triage loop (`reportImageUris[]`); multi-page = multiple object keys. (spec §4)
- **No AI attribution** in commits or code (ProjectPlan §14.11 — no Co-Authored-By/AI trailers).
- ml-service tests: `cd apps/ml-service && ./.venv/Scripts/python.exe -m pytest`. api tests: `cd apps/api && ./.venv/Scripts/python.exe -m pytest`. mobile: `cd apps/mobile && npm test` + `npx tsc --noEmit`.
- Native-module tasks need a dev build (`expo prebuild` + EAS dev client) and a **physical-device manual gate** — the scanner cannot run in jest/Expo Go.

---

## Phase 1 — Camera scan + gallery + multi-page (reuses the existing pipeline)

### Task 1: `/v1/uploads/sign` accepts capture source + extension

**Files:**
- Modify: `apps/api/app/routers/uploads.py`
- Test: `apps/api/tests/test_uploads.py`

**Interfaces:**
- Produces: `POST /v1/uploads/sign` body `{ "source"?: "scan"|"upload", "ext"?: "webp"|"pdf"|"jpg"|"png" }` → `{ url, objectKey }` where `objectKey == reports/<source>/<userId>/<uuid>.<ext>` (defaults `source="upload"`, `ext="webp"`).

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_uploads.py  (add these; keep the existing test)
def _auth(token):
    return {"Authorization": f"Bearer {token}"}

def test_sign_defaults_to_upload_webp(client, patient_token, monkeypatch):
    from app.services import storage_service
    monkeypatch.setattr(storage_service, "presign_put", lambda key: f"http://minio/{key}?sig=x")
    r = client.post("/v1/uploads/sign", json={}, headers=_auth(patient_token))
    assert r.status_code == 200
    key = r.json()["objectKey"]
    assert key.startswith("reports/upload/")
    assert key.endswith(".webp")

def test_sign_scan_pdf_prefix_and_ext(client, patient_token, monkeypatch):
    from app.services import storage_service
    monkeypatch.setattr(storage_service, "presign_put", lambda key: f"http://minio/{key}?sig=x")
    r = client.post("/v1/uploads/sign", json={"source": "scan", "ext": "pdf"}, headers=_auth(patient_token))
    key = r.json()["objectKey"]
    assert key.startswith("reports/scan/")
    assert key.endswith(".pdf")

def test_sign_rejects_bad_source(client, patient_token, monkeypatch):
    from app.services import storage_service
    monkeypatch.setattr(storage_service, "presign_put", lambda key: "x")
    r = client.post("/v1/uploads/sign", json={"source": "evil", "ext": "exe"}, headers=_auth(patient_token))
    assert r.status_code == 422
```

> `client`, `patient_token` are from `apps/api/tests/conftest.py`; auth is the `Authorization: Bearer <token>` header exactly as the existing `test_sign_returns_url_and_key` does.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/test_uploads.py -v`
Expected: FAIL (new keys/validation not implemented).

- [ ] **Step 3: Write minimal implementation**

```python
# apps/api/app/routers/uploads.py
import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.deps import require_role
from app.models import User
from app.services import storage_service

router = APIRouter(prefix="/v1/uploads", tags=["uploads"])


class SignRequest(BaseModel):
    source: Literal["scan", "upload"] = "upload"
    ext: Literal["webp", "pdf", "jpg", "png"] = "webp"


@router.post("/sign")
def sign(body: SignRequest | None = None, user: User = Depends(require_role("patient"))) -> dict:
    body = body or SignRequest()
    key = f"reports/{body.source}/{user.id}/{uuid.uuid4()}.{body.ext}"
    return {"url": storage_service.presign_put(key), "objectKey": key}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/test_uploads.py -v`
Expected: PASS (old + 3 new).

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/routers/uploads.py apps/api/tests/test_uploads.py
git commit -m "uploads: sign accepts capture source + extension in the object key"
```

---

### Task 2: Add scanner + document-picker dependencies and Expo plugin config

**Files:**
- Modify: `apps/mobile/package.json` (deps)
- Modify: `apps/mobile/app.json` (plugins + permission)

**Interfaces:**
- Produces: `scanDocument` from `react-native-document-scanner-plugin`; `expo-document-picker`; `expo-image-picker` (already present) available to later tasks.

- [ ] **Step 1: Install the dependencies**

Run:
```bash
cd apps/mobile && npm install react-native-document-scanner-plugin expo-document-picker
```
Expected: both added to `package.json` dependencies.

- [ ] **Step 2: Add the config plugin + camera permission to `app.json`**

In `apps/mobile/app.json`, add to the `expo.plugins` array (after the webrtc entry):

```json
[
  "react-native-document-scanner-plugin",
  { "cameraPermission": "NADI needs the camera to scan your lab reports." }
]
```

(The iOS `NSCameraUsageDescription` and Android `CAMERA` permission already exist for video — no change needed there.)

- [ ] **Step 3: Verify typecheck + config resolves**

Run:
```bash
cd apps/mobile && npx tsc --noEmit
```
Expected: PASS (no type errors from the new imports being present).

> Manual gate (physical device, later): `npx expo prebuild --clean` then an EAS dev build must succeed and open the native scanner. Record in the verification doc; not blocking for unit work.

- [ ] **Step 4: Commit**

```bash
git add apps/mobile/package.json apps/mobile/package-lock.json apps/mobile/app.json
git commit -m "mobile: add document-scanner + document-picker deps and scanner plugin config"
```

---

### Task 3: `upload.ts` branches by file type; client sends capture source

**Files:**
- Modify: `apps/mobile/src/lib/upload.ts`
- Modify: `apps/mobile/src/api/patient.ts` (`signUpload`)
- Test: `apps/mobile/src/lib/__tests__/upload.test.ts`

**Interfaces:**
- Consumes: `signUpload({ source, ext })` → `{ url, objectKey }` (Task 1).
- Produces: `uploadReport(localUri: string, opts: { kind: 'image' | 'pdf'; source: 'scan' | 'upload' }): Promise<string>` (returns objectKey). `signUpload(body?: { source?: 'scan'|'upload'; ext?: 'webp'|'pdf'|'jpg'|'png' })`.

- [ ] **Step 1: Write the failing test**

```ts
// apps/mobile/src/lib/__tests__/upload.test.ts  (add; keep existing cases)
import { uploadReport } from '@/lib/upload';

jest.mock('@/api/patient', () => ({
  signUpload: jest.fn(),
}));
jest.mock('expo-image-manipulator', () => ({
  manipulateAsync: jest.fn(async (uri) => ({ uri: uri + '#webp' })),
  SaveFormat: { WEBP: 'webp' },
}));
import { signUpload } from '@/api/patient';

beforeEach(() => {
  (global as any).fetch = jest.fn(async (url: string, init?: any) => {
    if (typeof url === 'string' && url.startsWith('http://minio')) return { ok: true, status: 200 } as any;
    return { blob: async () => new Blob(['x']) } as any;
  });
});

test('pdf uploads verbatim with application/pdf and upload source', async () => {
  (signUpload as jest.Mock).mockResolvedValue({ url: 'http://minio/k.pdf', objectKey: 'reports/upload/u/k.pdf' });
  const key = await uploadReport('file:///report.pdf', { kind: 'pdf', source: 'upload' });
  expect(signUpload).toHaveBeenCalledWith({ source: 'upload', ext: 'pdf' });
  const putCall = (fetch as jest.Mock).mock.calls.find((c) => c[0] === 'http://minio/k.pdf');
  expect(putCall[1].headers['content-type']).toBe('application/pdf');
  expect(key).toBe('reports/upload/u/k.pdf');
});

test('scanned image is webp with scan source', async () => {
  (signUpload as jest.Mock).mockResolvedValue({ url: 'http://minio/k.webp', objectKey: 'reports/scan/u/k.webp' });
  const key = await uploadReport('file:///page1.jpg', { kind: 'image', source: 'scan' });
  expect(signUpload).toHaveBeenCalledWith({ source: 'scan', ext: 'webp' });
  const putCall = (fetch as jest.Mock).mock.calls.find((c) => c[0] === 'http://minio/k.webp');
  expect(putCall[1].headers['content-type']).toBe('image/webp');
  expect(key).toBe('reports/scan/u/k.webp');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/mobile && npm test -- upload.test.ts`
Expected: FAIL (`uploadReport` signature/branching not implemented).

- [ ] **Step 3: Write minimal implementation**

```ts
// apps/mobile/src/lib/upload.ts
import * as ImageManipulator from 'expo-image-manipulator';
import { signUpload } from '@/api/patient';

export class UploadError extends Error {
  constructor(public kind: 'storage' | 'network', message: string) { super(message); }
}

type UploadOpts = { kind: 'image' | 'pdf'; source: 'scan' | 'upload' };

export async function uploadReport(localUri: string, opts: UploadOpts): Promise<string> {
  let body: Blob;
  let contentType: string;
  let ext: 'webp' | 'pdf';

  if (opts.kind === 'pdf') {
    ext = 'pdf';
    contentType = 'application/pdf';
    try {
      const r = await fetch(localUri);
      body = await r.blob();
    } catch { throw new UploadError('network', 'could not read file'); }
  } else {
    ext = 'webp';
    contentType = 'image/webp';
    const edited = await ImageManipulator.manipulateAsync(
      localUri, [{ resize: { width: 1600 } }],
      { compress: 0.75, format: ImageManipulator.SaveFormat.WEBP },
    );
    try {
      const r = await fetch(edited.uri);
      body = await r.blob();
    } catch { throw new UploadError('network', 'could not read image'); }
  }

  const { url, objectKey } = await signUpload({ source: opts.source, ext });
  let put: Response;
  try {
    put = await fetch(url, { method: 'PUT', headers: { 'content-type': contentType }, body });
  } catch { throw new UploadError('network', 'could not reach storage'); }
  if (!put.ok) throw new UploadError('storage', `storage rejected upload (${put.status})`);
  return objectKey;
}
```

```ts
// apps/mobile/src/api/patient.ts  — replace the signUpload export
export const signUpload = (body?: { source?: 'scan' | 'upload'; ext?: 'webp' | 'pdf' | 'jpg' | 'png' }) =>
  api.post('/v1/uploads/sign', body ?? {}, z.object({ url: z.string(), objectKey: z.string() }));
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd apps/mobile && npm test -- upload.test.ts && npx tsc --noEmit`
Expected: PASS. (Note: `useReportUploads.ts` calls `uploadReport(uri)` — it is updated in Task 4; until then tsc may flag that call site. Run tsc after Task 4, or update the call in this commit per Step 5.)

- [ ] **Step 5: Update the one existing caller and commit**

In `apps/mobile/src/features/patient/useReportUploads.ts`, change the `Item` type and `add`/`run` to carry `kind` + `source`:

```ts
type Item = { id: string; uri: string; kind: 'image' | 'pdf'; source: 'scan' | 'upload';
              status: 'uploading' | 'done' | 'error'; objectKey?: string };

const run = useCallback(async (it: Item) => {
  patch(it.id, { status: 'uploading' });
  try { patch(it.id, { status: 'done', objectKey: await uploadReport(it.uri, { kind: it.kind, source: it.source }) }); }
  catch { patch(it.id, { status: 'error' }); }
}, []);

const add = useCallback((uri: string, kind: 'image' | 'pdf', source: 'scan' | 'upload') => {
  const id = `r${seq++}`;
  const it: Item = { id, uri, kind, source, status: 'uploading' };
  setItems((xs) => [...xs, it]);
  void run(it);
}, [run]);

const retry = useCallback((id: string) => {
  const it = items.find((x) => x.id === id);
  if (it) void run(it);
}, [items, run]);
```

```bash
cd apps/mobile && npm test -- upload.test.ts && npx tsc --noEmit
git add apps/mobile/src/lib/upload.ts apps/mobile/src/api/patient.ts apps/mobile/src/features/patient/useReportUploads.ts apps/mobile/src/lib/__tests__/upload.test.ts
git commit -m "mobile: upload branches image/pdf and tags capture source"
```

---

### Task 4: Capture sheet (Scan / Gallery / File) wired into the reports screen

**Files:**
- Create: `apps/mobile/src/features/patient/capture.ts` (pure helpers)
- Create: `apps/mobile/src/components/CaptureSheet.tsx`
- Modify: `apps/mobile/app/(patient)/reports.tsx`
- Test: `apps/mobile/src/features/patient/__tests__/capture.test.ts`

**Interfaces:**
- Consumes: `add(uri, kind, source)` from `useReportUploads` (Task 3); `scanDocument` (plugin), `expo-image-picker`, `expo-document-picker`.
- Produces: `classifyPicked(name: string | undefined, mimeType?: string): 'image' | 'pdf'`; `<CaptureSheet onPicked={(items: { uri: string; kind: 'image'|'pdf'; source: 'scan'|'upload' }[]) => void} />`.

- [ ] **Step 1: Write the failing test (pure classifier)**

```ts
// apps/mobile/src/features/patient/__tests__/capture.test.ts
import { classifyPicked } from '@/features/patient/capture';

test('classifies pdf by mime', () => {
  expect(classifyPicked('r.pdf', 'application/pdf')).toBe('pdf');
});
test('classifies pdf by extension when mime missing', () => {
  expect(classifyPicked('scan_001.PDF', undefined)).toBe('pdf');
});
test('defaults to image', () => {
  expect(classifyPicked('photo.jpg', 'image/jpeg')).toBe('image');
  expect(classifyPicked(undefined, undefined)).toBe('image');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/mobile && npm test -- capture.test.ts`
Expected: FAIL (`capture.ts` does not exist).

- [ ] **Step 3: Implement the pure helper**

```ts
// apps/mobile/src/features/patient/capture.ts
export function classifyPicked(name: string | undefined, mimeType?: string): 'image' | 'pdf' {
  if (mimeType === 'application/pdf') return 'pdf';
  if (name && name.toLowerCase().endsWith('.pdf')) return 'pdf';
  return 'image';
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/mobile && npm test -- capture.test.ts`
Expected: PASS.

- [ ] **Step 5: Implement the CaptureSheet component**

```tsx
// apps/mobile/src/components/CaptureSheet.tsx
import { Pressable, Text, View } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import * as DocumentPicker from 'expo-document-picker';
import scanDocument from 'react-native-document-scanner-plugin';
import { classifyPicked } from '@/features/patient/capture';
import { colors, radii, spacing, type as t } from '@/theme/tokens';

export type Picked = { uri: string; kind: 'image' | 'pdf'; source: 'scan' | 'upload' };

export function CaptureSheet({ onPicked }: { onPicked: (items: Picked[]) => void }) {
  const scan = async () => {
    const { scannedImages } = await scanDocument({ maxNumDocuments: 10 });
    if (scannedImages?.length) onPicked(scannedImages.map((uri) => ({ uri, kind: 'image', source: 'scan' })));
  };
  const gallery = async () => {
    const res = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images, allowsMultipleSelection: true, quality: 1,
    });
    if (!res.canceled) onPicked(res.assets.map((a) => ({ uri: a.uri, kind: 'image', source: 'upload' })));
  };
  const file = async () => {
    const res = await DocumentPicker.getDocumentAsync({ type: ['application/pdf', 'image/*'], multiple: true });
    if (!res.canceled) onPicked(res.assets.map((a) => ({
      uri: a.uri, kind: classifyPicked(a.name, a.mimeType), source: 'upload',
    })));
  };
  const Item = ({ label, onPress }: { label: string; onPress: () => void }) => (
    <Pressable onPress={onPress} style={{ paddingVertical: spacing.md, paddingHorizontal: spacing.lg,
      backgroundColor: colors.surface, borderRadius: radii.lg, borderWidth: 1, borderColor: colors.border }}>
      <Text style={{ fontSize: t.body, fontWeight: '700', color: colors.text }}>{label}</Text>
    </Pressable>
  );
  return (
    <View style={{ gap: spacing.sm }}>
      <Item label="Scan with camera" onPress={scan} />
      <Item label="Choose from gallery" onPress={gallery} />
      <Item label="Upload a file (PDF/image)" onPress={file} />
    </View>
  );
}
```

- [ ] **Step 6: Wire it into `reports.tsx`**

```tsx
// apps/mobile/app/(patient)/reports.tsx  — replace the single picker with the sheet
import { Image, Pressable, ScrollView, Text, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Button } from '@/components/ui';
import { CaptureSheet, type Picked } from '@/components/CaptureSheet';
import { useReportUploads } from '@/features/patient/useReportUploads';
import { useTheme } from '@/providers/ThemeProvider';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function Reports() {
  const theme = useTheme();
  const { symptomText, lang } = useLocalSearchParams<{ symptomText: string; lang: string }>();
  const { items, add, remove, retry, allSettled, objectKeys } = useReportUploads();
  const onPicked = (picked: Picked[]) => picked.forEach((p) => add(p.uri, p.kind, p.source));
  const go = () => router.push({ pathname: '/(patient)/analyzing',
    params: { symptomText, lang, keys: JSON.stringify(objectKeys) } });
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.h2, color: theme.primary, fontWeight: '700' }}>Lab reports (optional)</Text>
      <Text style={{ fontSize: t.sm, color: colors.textMuted }}>Scan, choose, or upload any recent reports — or skip.</Text>
      <CaptureSheet onPicked={onPicked} />
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm }}>
        {items.map((it) => (
          <View key={it.id} style={{ width: 96 }}>
            {it.kind === 'image'
              ? <Image source={{ uri: it.uri }} style={{ width: 96, height: 96, borderRadius: 8 }} />
              : <View style={{ width: 96, height: 96, borderRadius: 8, backgroundColor: colors.greenTint, alignItems: 'center', justifyContent: 'center' }}><Text style={{ fontWeight: '800', color: colors.text }}>PDF</Text></View>}
            <Text style={{ fontSize: t.xs, color: it.status === 'error' ? colors.emergency : colors.textMuted }}>
              {it.status === 'uploading' ? 'Uploading…' : it.status === 'done' ? 'Ready' : 'Failed — tap retry'}
            </Text>
            {it.status === 'error' ? <Pressable onPress={() => retry(it.id)}><Text style={{ color: theme.primary }}>Retry</Text></Pressable> : null}
            <Pressable onPress={() => remove(it.id)}><Text style={{ color: colors.textMuted }}>Remove</Text></Pressable>
          </View>
        ))}
      </View>
      <Button title="Continue" onPress={go} color={theme.primary} disabled={!allSettled} />
    </ScrollView>
  );
}
```

- [ ] **Step 7: Typecheck, test, commit**

Run: `cd apps/mobile && npm test -- capture.test.ts && npx tsc --noEmit`
Expected: PASS.

```bash
git add apps/mobile/src/features/patient/capture.ts apps/mobile/src/components/CaptureSheet.tsx apps/mobile/app/(patient)/reports.tsx apps/mobile/src/features/patient/__tests__/capture.test.ts
git commit -m "mobile: capture sheet with scan/gallery/file and multi-page"
```

> Manual gate (device): verify the native scanner opens, multi-page capture works, and PDF/gallery picks upload. Add to `docs/superpowers/verification/`.

---

## Phase 2 — PDF support (server-side rasterization + multi-page OCR)

### Task 5: `pypdfium2` dependency + `preprocess.load_document`

**Files:**
- Modify: `apps/ml-service/pyproject.toml` (add `pypdfium2`)
- Modify: `apps/ml-service/app/ocr/preprocess.py`
- Test: `apps/ml-service/tests/test_preprocess.py`

**Interfaces:**
- Consumes: existing `load_and_validate(data: bytes) -> Image`.
- Produces: `load_document(data: bytes, *, max_pages: int = 10, dpi: int = 200) -> list[Image.Image]` — PDF (magic `%PDF`) → one RGB image per page (capped); any other bytes → `[load_and_validate(data)]`.

- [ ] **Step 1: Install the dependency**

Run:
```bash
cd apps/ml-service && ./.venv/Scripts/python.exe -m pip install "pypdfium2>=4"
```
Then add `"pypdfium2>=4"` to the `dependencies` list in `pyproject.toml`.

- [ ] **Step 2: Write the failing test**

```python
# apps/ml-service/tests/test_preprocess.py  (add; keep existing cases)
import io
from PIL import Image
from app.ocr.preprocess import load_document


def _pdf_bytes(pages: int = 1) -> bytes:
    imgs = [Image.new("RGB", (240, 320), "white") for _ in range(pages)]
    buf = io.BytesIO()
    imgs[0].save(buf, format="PDF", save_all=True, append_images=imgs[1:])
    return buf.getvalue()


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (100, 100), "white").save(buf, format="PNG")
    return buf.getvalue()


def test_load_document_image_returns_single_image():
    out = load_document(_png_bytes())
    assert len(out) == 1 and out[0].mode == "RGB"


def test_load_document_pdf_rasterizes_each_page():
    out = load_document(_pdf_bytes(pages=3))
    assert len(out) == 3
    assert all(im.mode == "RGB" for im in out)


def test_load_document_pdf_page_cap():
    out = load_document(_pdf_bytes(pages=15), max_pages=10)
    assert len(out) == 10
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd apps/ml-service && ./.venv/Scripts/python.exe -m pytest tests/test_preprocess.py -v`
Expected: FAIL (`load_document` not defined).

- [ ] **Step 4: Write minimal implementation**

```python
# apps/ml-service/app/ocr/preprocess.py  (append; keep load_and_validate as-is)
import pypdfium2 as pdfium


def load_document(data: bytes, *, max_pages: int = 10, dpi: int = 200) -> list[Image.Image]:
    """PDF (magic %PDF) -> one RGB image per page (capped). Any other bytes ->
    [load_and_validate(data)]. Raises InvalidImageError on empty/corrupt input."""
    if not data:
        raise InvalidImageError("empty file")
    if data[:4] != b"%PDF":
        return [load_and_validate(data)]
    try:
        pdf = pdfium.PdfDocument(data)
    except Exception as exc:  # noqa: BLE001
        raise InvalidImageError("unsupported or corrupt pdf") from exc
    scale = dpi / 72.0
    images: list[Image.Image] = []
    for i in range(min(len(pdf), max_pages)):
        bitmap = pdf[i].render(scale=scale)
        images.append(bitmap.to_pil().convert("RGB"))
    return images
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd apps/ml-service && ./.venv/Scripts/python.exe -m pytest tests/test_preprocess.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/ml-service/pyproject.toml apps/ml-service/app/ocr/preprocess.py apps/ml-service/tests/test_preprocess.py
git commit -m "ml-service: rasterize PDFs to page images via pypdfium2 (load_document)"
```

---

### Task 6: `extract_report` handles multiple pages

**Files:**
- Modify: `apps/ml-service/app/ocr/pipeline.py`
- Test: `apps/ml-service/tests/test_pipeline.py`

**Interfaces:**
- Consumes: `load_document` (Task 5), existing `run_ocr`, `parse_fields`, `normalize_fields`, `to_labs`.
- Produces: `extract_report(object_key, *, ocr_fn=None)` unchanged signature; now concatenates fields/warnings across all pages of a (possibly multi-page) document. Single-image documents behave exactly as before.

- [ ] **Step 1: Write the failing test**

```python
# apps/ml-service/tests/test_pipeline.py  (add; keep existing cases)
import io
from PIL import Image
from app.ocr import pipeline, storage


def _pdf_bytes(pages: int = 2) -> bytes:
    imgs = [Image.new("RGB", (240, 320), "white") for _ in range(pages)]
    buf = io.BytesIO()
    imgs[0].save(buf, format="PDF", save_all=True, append_images=imgs[1:])
    return buf.getvalue()


def test_extract_report_concatenates_fields_across_pdf_pages(monkeypatch):
    monkeypatch.setattr(storage, "fetch_object", lambda key: _pdf_bytes(pages=2))
    # one OCR "line" per page -> a parseable row "Haemoglobin 9.1 g/dL 12.0 - 15.5"
    def fake_ocr(_image):
        return [
            {"text": "Haemoglobin", "box": [10, 100, 120, 30], "conf": 0.95},
            {"text": "9.1", "box": [200, 100, 40, 30], "conf": 0.95},
            {"text": "g/dL", "box": [260, 100, 50, 30], "conf": 0.95},
            {"text": "12.0 - 15.5", "box": [340, 100, 120, 30], "conf": 0.95},
        ]
    res = pipeline.extract_report("reports/upload/u/doc.pdf", ocr_fn=fake_ocr)
    # 2 pages -> 2 Haemoglobin fields
    assert len(res["fields"]) == 2
    assert all(f["testNameNormalized"] == "Haemoglobin" for f in res["fields"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/ml-service && ./.venv/Scripts/python.exe -m pytest tests/test_pipeline.py -v`
Expected: FAIL (currently single-image; PDF bytes would fail `load_and_validate`).

- [ ] **Step 3: Write minimal implementation**

```python
# apps/ml-service/app/ocr/pipeline.py  — update imports + extract_report body
import logging
import time

from app.ocr import storage
from app.ocr.engine import MODEL_VERSION, run_ocr
from app.ocr.normalize import normalize_fields
from app.ocr.parse import parse_fields
from app.ocr.preprocess import load_document

logger = logging.getLogger(__name__)


def to_labs(fields: list[dict]) -> list[dict]:
    labs = []
    for f in fields:
        if f["valueNumeric"] is None or "unknown_analyte" in f["qualityFlags"] or not f["flag"]:
            continue
        labs.append({
            "analyte": f["testNameNormalized"], "value": f["valueNumeric"],
            "unit": f["unit"], "refRange": f["referenceRangeRaw"], "flag": f["flag"],
        })
    return labs


def _safe_result(latency_ms: int) -> dict:
    return {"labs": [], "fields": [], "needsReview": True, "warnings": ["extraction_failed"],
            "modelVersion": MODEL_VERSION, "latencyMs": latency_ms}


def extract_report(object_key: str, *, ocr_fn=None) -> dict:
    ocr_fn = ocr_fn or run_ocr
    start = time.monotonic()
    try:
        images = load_document(storage.fetch_object(object_key))
        fields: list[dict] = []
        warnings: list[str] = []
        for image in images:
            norm = normalize_fields(parse_fields(ocr_fn(image)))
            fields.extend(norm["fields"])
            warnings.extend(norm["warnings"])
        labs = to_labs(fields)
        needs_review = (not fields or any(f["qualityFlags"] for f in fields) or len(labs) < len(fields))
        return {
            "labs": labs, "fields": fields, "needsReview": needs_review,
            "warnings": warnings, "modelVersion": MODEL_VERSION,
            "latencyMs": int((time.monotonic() - start) * 1000),
        }
    except Exception as exc:  # noqa: BLE001 — never crash the consultation flow
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.warning("ocr_extraction_failed exc_type=%s latency_ms=%d", type(exc).__name__, latency_ms)
        return _safe_result(latency_ms)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd apps/ml-service && ./.venv/Scripts/python.exe -m pytest tests/test_pipeline.py tests/test_document_endpoint.py -v`
Expected: PASS (multi-page concat + existing single-image behavior intact).

- [ ] **Step 5: Commit**

```bash
git add apps/ml-service/app/ocr/pipeline.py apps/ml-service/tests/test_pipeline.py
git commit -m "ml-service: OCR all pages of a document and concatenate fields"
```

---

## Phase 3 — Server-side enhancement (upload path only)

### Task 7: `preprocess.enhance` + apply to `/upload/` keys

**Files:**
- Modify: `apps/ml-service/app/ocr/preprocess.py`
- Modify: `apps/ml-service/app/ocr/pipeline.py`
- Test: `apps/ml-service/tests/test_preprocess.py`, `apps/ml-service/tests/test_pipeline.py`

**Interfaces:**
- Produces: `enhance(img: Image.Image) -> Image.Image` — grayscale + CLAHE contrast, returned as RGB (same dimensions). Applied in `extract_report` only when `"/upload/" in object_key`.

> Scope note: deskew is intentionally **not** included here — a fragile auto-rotation risks degrading good scans. Grayscale + CLAHE is the robust, testable win; deskew can be a later refinement.

- [ ] **Step 1: Write the failing test**

```python
# apps/ml-service/tests/test_preprocess.py  (add)
from PIL import Image
from app.ocr.preprocess import enhance


def test_enhance_returns_same_size_rgb():
    out = enhance(Image.new("RGB", (120, 90), "gray"))
    assert out.mode == "RGB"
    assert out.size == (120, 90)
```

```python
# apps/ml-service/tests/test_pipeline.py  (add)
from unittest.mock import patch
from app.ocr import pipeline, storage


def test_extract_report_enhances_only_upload_keys(monkeypatch):
    monkeypatch.setattr(storage, "fetch_object", lambda key: _png_bytes())
    calls = {"n": 0}
    def spy_enhance(img):
        calls["n"] += 1
        return img
    with patch.object(pipeline, "enhance", spy_enhance):
        pipeline.extract_report("reports/scan/u/a.webp", ocr_fn=lambda im: [])
        assert calls["n"] == 0  # scan source: no enhancement
        pipeline.extract_report("reports/upload/u/a.webp", ocr_fn=lambda im: [])
        assert calls["n"] == 1  # upload source: enhanced

def _png_bytes() -> bytes:
    import io
    from PIL import Image
    buf = io.BytesIO(); Image.new("RGB", (80, 80), "white").save(buf, format="PNG"); return buf.getvalue()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/ml-service && ./.venv/Scripts/python.exe -m pytest tests/test_preprocess.py tests/test_pipeline.py -v`
Expected: FAIL (`enhance` not defined; pipeline does not import/apply it).

- [ ] **Step 3: Implement `enhance`**

```python
# apps/ml-service/app/ocr/preprocess.py  (append)
import cv2
import numpy as np


def enhance(img: Image.Image) -> Image.Image:
    """Grayscale + CLAHE contrast for noisy uploaded photos. Returns RGB, same size."""
    arr = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    eq = clahe.apply(arr)
    rgb = cv2.cvtColor(eq, cv2.COLOR_GRAY2RGB)
    return Image.fromarray(rgb)
```

- [ ] **Step 4: Apply it in the pipeline**

```python
# apps/ml-service/app/ocr/pipeline.py  — import and apply
from app.ocr.preprocess import enhance, load_document
```

In `extract_report`, replace the page loop with:

```python
        images = load_document(storage.fetch_object(object_key))
        if "/upload/" in object_key:
            images = [enhance(im) for im in images]
        fields: list[dict] = []
        warnings: list[str] = []
        for image in images:
            norm = normalize_fields(parse_fields(ocr_fn(image)))
            fields.extend(norm["fields"])
            warnings.extend(norm["warnings"])
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd apps/ml-service && ./.venv/Scripts/python.exe -m pytest tests/ -v`
Expected: PASS (full ml-service suite).

- [ ] **Step 6: Commit**

```bash
git add apps/ml-service/app/ocr/preprocess.py apps/ml-service/app/ocr/pipeline.py apps/ml-service/tests/test_preprocess.py apps/ml-service/tests/test_pipeline.py
git commit -m "ml-service: CLAHE enhancement for uploaded (non-scan) report images"
```

---

## Persistence (spec §5.4) — store the full extraction per report

### Task 8: `Report.extraction_json` column + migration

**Files:**
- Modify: `apps/api/app/models/consultation.py` (Report model)
- Create: `apps/api/migrations/versions/0009_report_extraction_json.py`
- Test: `apps/api/tests/test_migrations_smoke.py` (or the existing migration/seed smoke test — see Step 1)

**Interfaces:**
- Produces: `Report.extraction_json: Mapped[str | None]` (nullable text column `extraction_json`).

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_report_extraction_column.py  (new)
from app.models import Report


def test_report_has_extraction_json_column():
    assert "extraction_json" in Report.__table__.columns
    assert Report.__table__.columns["extraction_json"].nullable is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/test_report_extraction_column.py -v`
Expected: FAIL (column missing).

- [ ] **Step 3: Add the model column**

```python
# apps/api/app/models/consultation.py  — in class Report, add after ocr_status
    extraction_json: Mapped[str | None] = mapped_column(String, nullable=True)
```

- [ ] **Step 4: Create the Alembic migration**

```python
# apps/api/migrations/versions/0009_report_extraction_json.py
"""report extraction_json

Revision ID: 0009_report_extraction_json
Revises: 0008_doctor_availability_profile
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_report_extraction_json"
down_revision: str | None = "0008_doctor_availability_profile"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("extraction_json", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("reports", "extraction_json")
```

- [ ] **Step 5: Run test + migration to verify**

Run:
```bash
cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/test_report_extraction_column.py -v
```
Expected: PASS. (Migration is exercised end-to-end by the stack's auto-migrate on startup; a fresh `make reset` / `alembic upgrade head` must succeed.)

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/models/consultation.py apps/api/migrations/versions/0009_report_extraction_json.py apps/api/tests/test_report_extraction_column.py
git commit -m "api: add Report.extraction_json column + migration 0009"
```

---

### Task 9: Persist full extraction at intake; `ml_client.document` returns the full result

**Files:**
- Modify: `apps/api/app/services/ml_client.py`
- Modify: `apps/api/app/services/consultation_service.py`
- Test: `apps/api/tests/test_consultations.py` (or the existing intake test module)

**Interfaces:**
- Consumes: ml-service `POST /ml/v1/document` → `{ labs, fields?, needsReview?, modelVersion?, ... }` (full dict for real OCR; `{labs}` for the stub).
- Produces: `ml_client.document(object_key) -> dict` (the full result). `intake()` persists `Report.extraction_json = json.dumps(result)` and still aggregates `result["labs"]`.

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_consultations.py  (add; uses conftest fixtures client/patient_token/db)
import json
import uuid
from sqlalchemy import select
from app.models import Report
from app.services import ml_client


def test_intake_persists_extraction_json(client, patient_token, db, monkeypatch):
    monkeypatch.setattr(
        ml_client, "document",
        lambda key: {"labs": [{"analyte": "Haemoglobin", "value": 9.1, "unit": "g/dL",
                                "refRange": "12.0 - 15.5", "flag": "L"}],
                     "fields": [{"testNameNormalized": "Haemoglobin"}], "needsReview": True,
                     "modelVersion": "test"},
    )
    monkeypatch.setattr(ml_client, "triage", lambda payload: {
        "acuity": "ROUTINE", "acuityConfidence": 0.6, "specialties": [], "drivers": [],
        "labs": [], "redFlags": [], "modelVersion": "stub"})
    r = client.post(
        "/v1/consultations/intake",
        json={"symptomText": "tired", "reportImageUris": ["reports/upload/u/a.webp"], "lang": "en"},
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert r.status_code == 200
    cid = uuid.UUID(r.json()["consultationId"])  # scope to THIS consultation — the DB has seeded reports
    rows = db.execute(select(Report).where(Report.consultation_id == cid)).scalars().all()
    assert len(rows) == 1
    saved = json.loads(rows[0].extraction_json)
    assert saved["needsReview"] is True
    assert saved["fields"][0]["testNameNormalized"] == "Haemoglobin"
```

> If `IntakeResultSchema` names the id field differently than `consultationId`, use that key (check `apps/api/app/schemas`). The query is scoped to the new consultation because seed data already contains `Report` rows.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/test_consultations.py -k extraction_json -v`
Expected: FAIL (`document` still returns a list; `extraction_json` never set).

- [ ] **Step 3: Make `ml_client.document` return the full result**

```python
# apps/api/app/services/ml_client.py  — replace document()
def document(object_key: str) -> dict:
    return _post("/ml/v1/document", {"objectKey": object_key})
```

- [ ] **Step 4: Persist it in intake**

```python
# apps/api/app/services/consultation_service.py
# add at top:
import json
# ... in intake(), replace the report loop body:
    labs: list[dict] = []
    for object_key in inp.reportImageUris:
        result = ml_client.document(object_key)
        db.add(
            Report(
                id=uuid.uuid4(),
                consultation_id=consult.id,
                object_key=object_key,
                ocr_status="done",
                extraction_json=json.dumps(result),
            )
        )
        labs.extend(result.get("labs", []))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/test_consultations.py -v`
Expected: PASS (new + existing intake tests).

- [ ] **Step 6: Run the full api suite + commit**

Run: `cd apps/api && ./.venv/Scripts/python.exe -m pytest`
Expected: PASS.

```bash
git add apps/api/app/services/ml_client.py apps/api/app/services/consultation_service.py apps/api/tests/test_consultations.py
git commit -m "api: persist full OCR extraction per report at intake"
```

---

## Final verification (after all tasks)

- [ ] `cd apps/ml-service && ./.venv/Scripts/python.exe -m pytest` — all green.
- [ ] `cd apps/api && ./.venv/Scripts/python.exe -m pytest` — all green.
- [ ] `cd apps/mobile && npm test && npx tsc --noEmit` — all green.
- [ ] Fresh stack migrates cleanly: `make reset` (or `docker compose ... up -d --build`) reaches `0009` with no error.
- [ ] Device gate (manual, record in `docs/superpowers/verification/`): dev build opens the native scanner; multi-page scan, gallery multi-select, and PDF upload each produce reports; with `ML_OCR_ENABLED=true` a scanned/PDF report extracts fields end-to-end.

## Spec coverage map

- §5.1 mobile scanner/gallery/file/multi-page → Tasks 2, 3, 4
- §5.2 api key source/ext → Task 1
- §5.3 ml-service PDF rasterize + enhance → Tasks 5, 6, 7
- §5.4 persist full extraction → Tasks 8, 9
- §6 phasing → Phase 1 (T1–4), Phase 2 (T5–6), Phase 3 (T7); persistence (T8–9)
- §8 risks (page cap/DPI, never-raise fallback, licensing) → Tasks 5, 6, Global Constraints

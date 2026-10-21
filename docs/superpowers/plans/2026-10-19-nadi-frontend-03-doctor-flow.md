# NADI Frontend — Plan 03: Doctor Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Depends on Plans 01–02.**

**Goal:** The doctor portal (navy theme) — a live acuity-sorted queue, the NADI Note patient file with the triage drivers and lab table, the ability to join the same jit.si room, write a prescription, or refer to another specialty.

**Architecture:** Thin expo-router screens under `app/(doctor)/`; network in `src/api/doctor.ts`; React Query polling for the queue. The queue item already embeds the full `TriageResult`, so the patient-file screen renders entirely from the cached queue item — no extra per-consultation fetch needed. No backend changes in this plan.

**Tech Stack:** Plan 01/02 stack; `@shopify/flash-list` for the queue; the shared `JitsiRoom` component + `roomName` (Plan 02 Task 12, amended) for in-app video.

> **Amended 2026-10-20:** the doctor joins the consultation with the same in-app Jitsi `JitsiRoom` the patient uses (Plan 02 Task 12), not an `expo-web-browser` redirect. Task 3's "Start consultation" now navigates to a doctor room screen (Task 6).

## Global Constraints

(Same as Plans 01–02 — repeated for self-containment.)

- TS strict; functional components <150 lines; no logic in route files; tokens only, no inline hex.
- Baseline 360×640; tap targets ≥48dp; primary buttons 56dp; body ≥15.
- Acuity always **badge + text label**, never colour alone.
- No AI/tool attribution; commits short, imperative, lowercase.
- **Routes, does not diagnose** — the NADI Note presents routing + drivers, never a diagnosis.
- Strictly $0; access token memory / refresh in SecureStore; **every response zod-parsed**.
- Skeletons not spinners; designed empty states.
- A doctor sees only patients **booked with them** (enforced server-side; the UI never implies broader access — ProjectPlan §11).

---

### Task 1: Doctor API module

**Files:**
- Create: `apps/mobile/src/api/doctor.ts`
- Test: `apps/mobile/src/api/__tests__/doctor.test.ts`

**Interfaces:**
- Consumes: `api`, `QueueItemSchema` (Plan 01 Task 5).
- Produces: `getQueue()` → `QueueItem[]`; `prescribe(consultationId, lines)` → `{ prescriptionId }`; `refer(consultationId, body)` → `{ referred }`.

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/api/__tests__/doctor.test.ts`:
```ts
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { getQueue, prescribe } from '@/api/doctor';
import { useSession } from '@/store/session';

const BASE = 'http://test.local';
process.env.EXPO_PUBLIC_API_URL = BASE;
const server = setupServer();
beforeAll(() => server.listen());
beforeEach(() => useSession.setState({ accessToken: 'a', refreshToken: 'r' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

const triage = { acuity: 'URGENT', acuityConfidence: 0.8, specialties: [], drivers: [], labs: [], redFlags: [], modelVersion: 's' };
const item = { id: 'q1', patientName: 'Ramesh', patientAge: 58, patientSex: 'M', acuity: 'URGENT',
  complaint: 'chest pain', bookedFor: '10:00', triage };

test('getQueue parses items', async () => {
  server.use(http.get(`${BASE}/v1/doctor/queue`, () => HttpResponse.json([item])));
  expect((await getQueue())[0]!.patientName).toBe('Ramesh');
});

test('prescribe returns an id', async () => {
  server.use(http.post(`${BASE}/v1/doctor/consultations/q1/prescribe`, () => HttpResponse.json({ prescriptionId: 'p1' })));
  expect((await prescribe('q1', [{ drug: 'Para', strength: '500mg', frequency: 'BD', durationDays: 3 }])).prescriptionId).toBe('p1');
});
```

- [ ] **Step 2: Run to verify it fails** → `npm test -- api/__tests__/doctor` FAIL.

- [ ] **Step 3: Implement**

`apps/mobile/src/api/doctor.ts`:
```ts
import { z } from 'zod';
import { api } from '@/api/client';
import { QueueItemSchema, type QueueItem } from '@/api/schemas';

export type PrescriptionLineInput = {
  drug: string; strength: string; frequency: string; durationDays: number; notes?: string;
};

export const getQueue = (): Promise<QueueItem[]> =>
  api.get('/v1/doctor/queue', z.array(QueueItemSchema));

export const prescribe = (consultationId: string, lines: PrescriptionLineInput[]) =>
  api.post(`/v1/doctor/consultations/${consultationId}/prescribe`, { lines },
    z.object({ prescriptionId: z.string() }));

export const refer = (consultationId: string, body: { toSpecialty: string; reason: string }) =>
  api.post(`/v1/doctor/consultations/${consultationId}/refer`, body,
    z.object({ referred: z.boolean() }));
```

- [ ] **Step 4: Run to verify it passes** → `npm test -- api/__tests__/doctor` PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/mobile/src/api/doctor.ts apps/mobile/src/api/__tests__/doctor.test.ts
git commit -m "add doctor api module"
```

---

### Task 2: Queue screen (live, acuity-sorted)

**Files:**
- Create: `apps/mobile/app/(doctor)/index.tsx`
- Create: `apps/mobile/src/features/doctor/useQueue.ts`
- Create: `apps/mobile/src/components/QueueRow.tsx`
- Test: `apps/mobile/src/features/doctor/__tests__/useQueue.test.tsx`

**Interfaces:**
- Consumes: `getQueue`, `pollInterval`.
- Produces: `useQueue()` polling every 4000 ms (always active while mounted); `QueueRow({ item, onPress })` with a coloured left border by acuity and an `AcuityBadge`; queue screen as a FlashList with an empty state. The backend already returns the list acuity-sorted.

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/features/doctor/__tests__/useQueue.test.tsx`:
```tsx
import { renderHook, waitFor } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useQueue } from '@/features/doctor/useQueue';

jest.mock('@/api/doctor', () => ({ getQueue: jest.fn(async () => [{ id: 'q1', patientName: 'Ramesh', acuity: 'URGENT' }]) }));
const wrap = ({ children }: { children: React.ReactNode }) =>
  <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>;

test('loads the queue', async () => {
  const { result } = renderHook(() => useQueue(), { wrapper: wrap });
  await waitFor(() => expect(result.current.data?.[0]?.patientName).toBe('Ramesh'));
});
```

- [ ] **Step 2: Run to verify it fails** → `npm test -- useQueue` FAIL.

- [ ] **Step 3: Implement hook + row**

`apps/mobile/src/features/doctor/useQueue.ts`:
```ts
import { useQuery } from '@tanstack/react-query';
import { getQueue } from '@/api/doctor';
import { pollInterval } from '@/lib/polling';
export function useQueue() {
  return useQuery({ queryKey: ['queue'], queryFn: getQueue, refetchInterval: () => pollInterval(true, 4000) });
}
```
`apps/mobile/src/components/QueueRow.tsx`:
```tsx
import { Pressable, Text, View } from 'react-native';
import { AcuityBadge, Card } from '@/components/ui';
import type { QueueItem } from '@/api/schemas';
import { acuityColor } from '@/theme/tokens';
import { colors, spacing, type as t } from '@/theme/tokens';

export function QueueRow({ item, onPress }: { item: QueueItem; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} style={{ marginBottom: spacing.sm }}>
      <View style={{ borderLeftWidth: 4, borderLeftColor: acuityColor(item.acuity), borderRadius: 14 }}>
        <Card>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
            <View style={{ flex: 1 }}>
              <Text style={{ fontSize: t.body, fontWeight: '700', color: colors.text }}>
                {item.patientName}, {item.patientAge}{item.patientSex}
              </Text>
              <Text style={{ fontSize: t.sm, color: colors.textMuted }} numberOfLines={1}>{item.complaint}</Text>
            </View>
            <AcuityBadge acuity={item.acuity} />
          </View>
        </Card>
      </View>
    </Pressable>
  );
}
```

- [ ] **Step 4: Build the queue screen**

`apps/mobile/app/(doctor)/index.tsx`:
```tsx
import { View } from 'react-native';
import { FlashList } from '@shopify/flash-list';
import { router } from 'expo-router';
import { QueueRow } from '@/components/QueueRow';
import { EmptyState, ErrorState, Skeleton } from '@/components/ui';
import { useQueue } from '@/features/doctor/useQueue';
import { useQueryClient } from '@tanstack/react-query';
import { spacing } from '@/theme/tokens';

export default function DoctorQueue() {
  const { data, isLoading, isError, refetch } = useQueue();
  const qc = useQueryClient();
  if (isLoading) return <View style={{ padding: spacing.lg, gap: spacing.sm }}>{[0, 1, 2].map((i) => <Skeleton key={i} height={88} />)}</View>;
  if (isError) return <ErrorState message="Could not load the queue." onRetry={refetch} />;
  return (
    <FlashList data={data ?? []} estimatedItemSize={100} keyExtractor={(i) => i.id}
      contentContainerStyle={{ padding: spacing.lg }}
      ListEmptyComponent={<EmptyState title="No patients in your queue" message="Booked patients will appear here." />}
      renderItem={({ item }) => <QueueRow item={item} onPress={() => {
        qc.setQueryData(['queueItem', item.id], item);
        router.push({ pathname: '/(doctor)/case/[cid]', params: { cid: item.id } });
      }} />} />
  );
}
```

- [ ] **Step 5: Run + commit**

Run: `npm test && npm run typecheck`
```bash
git add apps/mobile/app/(doctor)/index.tsx apps/mobile/src/features/doctor/useQueue.ts apps/mobile/src/components/QueueRow.tsx apps/mobile/src/features/doctor/__tests__/useQueue.test.tsx
git commit -m "add doctor queue screen"
```

---

### Task 3: Patient file (NADI Note) + actions

**Files:**
- Create: `apps/mobile/app/(doctor)/case/[cid].tsx`
- Create: `apps/mobile/src/components/NadiNote.tsx`
- Test: `apps/mobile/src/components/__tests__/NadiNote.test.tsx`

**Interfaces:**
- Consumes: the cached `QueueItem` (`['queueItem', cid]`), falling back to a queue re-fetch; navigates to the doctor room screen (Task 6) for video.
- Produces: `NadiNote({ triage })` — the distinctly-styled card showing acuity + confidence %, recommended specialty, and drivers; patient-file screen with the note, a lab table, and three actions (join consultation / prescribe / refer).

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/components/__tests__/NadiNote.test.tsx`:
```tsx
import { render, screen } from '@testing-library/react-native';
import { NadiNote } from '@/components/NadiNote';

const triage = {
  acuity: 'URGENT', acuityConfidence: 0.82,
  specialties: [{ name: 'Cardiology', score: 0.8 }], drivers: [{ feature: 'chest pain', contribution: 0.5 }],
  labs: [], redFlags: [], modelVersion: 'stub',
} as any;

test('shows acuity label and confidence percent', () => {
  render(<NadiNote triage={triage} />);
  expect(screen.getByText('Urgent')).toBeOnTheScreen();
  expect(screen.getByText(/82%/)).toBeOnTheScreen();
});
```

- [ ] **Step 2: Run to verify it fails** → `npm test -- NadiNote` FAIL.

- [ ] **Step 3: Implement the note**

`apps/mobile/src/components/NadiNote.tsx`:
```tsx
import { Text, View } from 'react-native';
import { AcuityBadge } from '@/components/ui';
import type { TriageResult } from '@/api/schemas';
import { colors, radii, spacing, type as t } from '@/theme/tokens';

export function NadiNote({ triage }: { triage: TriageResult }) {
  const top = triage.specialties[0];
  return (
    <View style={{ backgroundColor: colors.lightBlue, borderRadius: radii.md, padding: spacing.md,
      borderWidth: 1, borderColor: colors.navy, gap: spacing.sm }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <Text style={{ fontSize: t.sm, color: colors.navy, fontWeight: '800' }}>NADI NOTE</Text>
        <AcuityBadge acuity={triage.acuity} />
      </View>
      <Text style={{ fontSize: t.body, color: colors.text }}>
        Suggested: {top?.name ?? '—'} · confidence {Math.round(triage.acuityConfidence * 100)}%
      </Text>
      <Text style={{ fontSize: t.xs, color: colors.navy }}>Drivers</Text>
      {triage.drivers.map((d, i) => (
        <Text key={i} style={{ fontSize: t.sm, color: colors.text }}>• {d.feature} ({Math.round(d.contribution * 100)}%)</Text>
      ))}
    </View>
  );
}
```

- [ ] **Step 4: Build the case screen**

`apps/mobile/app/(doctor)/case/[cid].tsx` (reads the cached queue item; uses `useQueue` as fallback):
```tsx
import { ScrollView, Text, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';
import { Button, Card } from '@/components/ui';
import { NadiNote } from '@/components/NadiNote';
import { useQueue } from '@/features/doctor/useQueue';
import type { QueueItem } from '@/api/schemas';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function DoctorCase() {
  const { cid } = useLocalSearchParams<{ cid: string }>();
  const qc = useQueryClient();
  const { data } = useQueue();
  const item = (qc.getQueryData<QueueItem>(['queueItem', cid])
    ?? data?.find((q) => q.id === cid)) as QueueItem | undefined;
  if (!item) return <View style={{ padding: spacing.lg }}><Text style={{ color: colors.textMuted }}>Loading case…</Text></View>;
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.h2, fontWeight: '700', color: colors.text }}>
        {item.patientName}, {item.patientAge}{item.patientSex}
      </Text>
      <Text style={{ fontSize: t.sm, color: colors.textMuted }}>Complaint: {item.complaint}</Text>
      <NadiNote triage={item.triage} />
      {item.triage.labs.length > 0 ? (
        <Card>
          <Text style={{ fontSize: t.sm, color: colors.textMuted }}>Labs</Text>
          {item.triage.labs.map((l, i) => (
            <Text key={i} style={{ fontSize: t.sm, color: l.flag === 'N' ? colors.text : colors.urgent }}>
              {l.analyte}: {l.value} {l.unit} [{l.refRange}] ({l.flag})
            </Text>
          ))}
        </Card>
      ) : null}
      <Button title="Start consultation" color={colors.navy}
        onPress={() => router.push({ pathname: '/(doctor)/room/[cid]', params: { cid: item.id } })} />
      <Button title="Write prescription" color={colors.navy}
        onPress={() => router.push({ pathname: '/(doctor)/prescribe/[cid]', params: { cid: item.id } })} />
      <Button title="Refer to another specialty" variant="ghost" color={colors.navy}
        onPress={() => router.push({ pathname: '/(doctor)/refer/[cid]', params: { cid: item.id } })} />
    </ScrollView>
  );
}
```

- [ ] **Step 5: Run + commit**

Run: `npm test && npm run typecheck`
```bash
git add apps/mobile/app/(doctor)/case apps/mobile/src/components/NadiNote.tsx apps/mobile/src/components/__tests__/NadiNote.test.tsx
git commit -m "add doctor patient-file screen with nadi note"
```

---

### Task 4: Prescription form

**Files:**
- Create: `apps/mobile/app/(doctor)/prescribe/[cid].tsx`
- Create: `apps/mobile/src/features/doctor/usePrescribe.ts`
- Test: `apps/mobile/src/features/doctor/__tests__/usePrescribe.test.ts`

**Interfaces:**
- Consumes: `prescribe`.
- Produces: `usePrescribe()` → `{ submit(cid, lines), pending }`; a form with add/remove medicine rows (drug, strength, frequency, durationDays) that submits and returns to the queue.

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/features/doctor/__tests__/usePrescribe.test.ts`:
```ts
import { renderHook, act } from '@testing-library/react-native';
import { usePrescribe } from '@/features/doctor/usePrescribe';
jest.mock('@/api/doctor', () => ({ prescribe: jest.fn(async () => ({ prescriptionId: 'p1' })) }));

test('submit returns the prescription id', async () => {
  const { result } = renderHook(() => usePrescribe());
  let id = '';
  await act(async () => { id = await result.current.submit('c1', [{ drug: 'Para', strength: '500mg', frequency: 'BD', durationDays: 3 }]); });
  expect(id).toBe('p1');
});
```

- [ ] **Step 2: Run to verify it fails** → `npm test -- usePrescribe` FAIL.

- [ ] **Step 3: Implement the hook**

`apps/mobile/src/features/doctor/usePrescribe.ts`:
```ts
import { useState } from 'react';
import { prescribe, type PrescriptionLineInput } from '@/api/doctor';
export function usePrescribe() {
  const [pending, setPending] = useState(false);
  const submit = async (cid: string, lines: PrescriptionLineInput[]): Promise<string> => {
    setPending(true);
    try { return (await prescribe(cid, lines)).prescriptionId; }
    finally { setPending(false); }
  };
  return { submit, pending };
}
```

- [ ] **Step 4: Build the form**

`apps/mobile/app/(doctor)/prescribe/[cid].tsx`:
```tsx
import { useState } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Button, Card, Input } from '@/components/ui';
import { usePrescribe } from '@/features/doctor/usePrescribe';
import type { PrescriptionLineInput } from '@/api/doctor';
import { colors, spacing, type as t } from '@/theme/tokens';

const blank = (): PrescriptionLineInput => ({ drug: '', strength: '', frequency: '', durationDays: 3 });

export default function Prescribe() {
  const { cid } = useLocalSearchParams<{ cid: string }>();
  const { submit, pending } = usePrescribe();
  const [lines, setLines] = useState<PrescriptionLineInput[]>([blank()]);
  const patch = (i: number, p: Partial<PrescriptionLineInput>) =>
    setLines((xs) => xs.map((x, j) => (j === i ? { ...x, ...p } : x)));
  const valid = lines.every((l) => l.drug.trim() && l.strength.trim() && l.frequency.trim());
  const save = async () => { await submit(cid!, lines); router.replace('/(doctor)'); };
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.h2, fontWeight: '700', color: colors.text }}>New prescription</Text>
      {lines.map((l, i) => (
        <Card key={i}>
          <Input value={l.drug} onChangeText={(v) => patch(i, { drug: v })} placeholder="Drug" />
          <Input value={l.strength} onChangeText={(v) => patch(i, { strength: v })} placeholder="Strength (e.g. 500mg)" />
          <Input value={l.frequency} onChangeText={(v) => patch(i, { frequency: v })} placeholder="Frequency (e.g. BD)" />
          <Input value={String(l.durationDays)} onChangeText={(v) => patch(i, { durationDays: Number(v) || 0 })} keyboardType="number-pad" placeholder="Days" />
          {lines.length > 1 ? <Pressable onPress={() => setLines((xs) => xs.filter((_, j) => j !== i))}>
            <Text style={{ color: colors.emergency }}>Remove</Text></Pressable> : null}
        </Card>
      ))}
      <Button title="+ Add medicine" variant="ghost" color={colors.navy} onPress={() => setLines((xs) => [...xs, blank()])} />
      <Button title="Issue prescription" color={colors.navy} loading={pending} disabled={!valid} onPress={save} />
    </ScrollView>
  );
}
```

- [ ] **Step 5: Run + commit**

Run: `npm test && npm run typecheck`
```bash
git add apps/mobile/app/(doctor)/prescribe apps/mobile/src/features/doctor/usePrescribe.ts apps/mobile/src/features/doctor/__tests__/usePrescribe.test.ts
git commit -m "add doctor prescription form"
```

---

### Task 5: Refer screen

**Files:**
- Create: `apps/mobile/app/(doctor)/refer/[cid].tsx`
- Create: `apps/mobile/src/features/doctor/useRefer.ts`
- Test: `apps/mobile/src/features/doctor/__tests__/useRefer.test.ts`

**Interfaces:**
- Consumes: `refer`.
- Produces: `useRefer()` → `{ submit(cid, toSpecialty, reason), pending }`; a small form (specialty + reason) that submits and returns to the queue.

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/features/doctor/__tests__/useRefer.test.ts`:
```ts
import { renderHook, act } from '@testing-library/react-native';
import { useRefer } from '@/features/doctor/useRefer';
jest.mock('@/api/doctor', () => ({ refer: jest.fn(async () => ({ referred: true })) }));

test('submit resolves true', async () => {
  const { result } = renderHook(() => useRefer());
  let ok = false;
  await act(async () => { ok = await result.current.submit('c1', 'Cardiology', 'needs ECG'); });
  expect(ok).toBe(true);
});
```

- [ ] **Step 2: Run to verify it fails** → `npm test -- useRefer` FAIL.

- [ ] **Step 3: Implement the hook**

`apps/mobile/src/features/doctor/useRefer.ts`:
```ts
import { useState } from 'react';
import { refer } from '@/api/doctor';
export function useRefer() {
  const [pending, setPending] = useState(false);
  const submit = async (cid: string, toSpecialty: string, reason: string): Promise<boolean> => {
    setPending(true);
    try { return (await refer(cid, { toSpecialty, reason })).referred; }
    finally { setPending(false); }
  };
  return { submit, pending };
}
```

- [ ] **Step 4: Build the screen**

`apps/mobile/app/(doctor)/refer/[cid].tsx`:
```tsx
import { useState } from 'react';
import { ScrollView, Text } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Button, Input } from '@/components/ui';
import { useRefer } from '@/features/doctor/useRefer';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function Refer() {
  const { cid } = useLocalSearchParams<{ cid: string }>();
  const { submit, pending } = useRefer();
  const [spec, setSpec] = useState('');
  const [reason, setReason] = useState('');
  const save = async () => { await submit(cid!, spec, reason); router.replace('/(doctor)'); };
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.h2, fontWeight: '700', color: colors.text }}>Refer patient</Text>
      <Input value={spec} onChangeText={setSpec} placeholder="Refer to specialty (e.g. Cardiology)" />
      <Input value={reason} onChangeText={setReason} multiline placeholder="Reason" />
      <Button title="Send referral" color={colors.navy} loading={pending}
        disabled={!spec.trim() || !reason.trim()} onPress={save} />
    </ScrollView>
  );
}
```

- [ ] **Step 5: Run + commit**

Run: `npm test && npm run typecheck`
```bash
git add apps/mobile/app/(doctor)/refer apps/mobile/src/features/doctor/useRefer.ts apps/mobile/src/features/doctor/__tests__/useRefer.test.ts
git commit -m "add doctor refer screen"
```

---

### Task 6: Doctor consultation room (in-app Jitsi)

The doctor joins the same deterministic room the patient joins, reusing the shared `JitsiRoom` built in Plan 02 Task 12. No new SDK work — the install/config landed in Plan 02.

**Files:**
- Create: `apps/mobile/app/(doctor)/room/[cid].tsx`

**Interfaces:**
- Consumes: `JitsiRoom` (Plan 02 Task 12), `useSession`.
- Produces: a doctor room screen at `/(doctor)/room/[cid]` that embeds the consultation `nadi-<cid>` room and returns to the case screen on close.

- [ ] **Step 1: Build the screen**

`apps/mobile/app/(doctor)/room/[cid].tsx`:
```tsx
import { router, useLocalSearchParams } from 'expo-router';
import { JitsiRoom } from '@/components/JitsiRoom';
import { useSession } from '@/store/session';

export default function DoctorRoom() {
  const { cid } = useLocalSearchParams<{ cid: string }>();
  const userId = useSession((s) => s.userId);
  return <JitsiRoom consultationId={cid!} displayName={`Doctor ${userId ?? ''}`.trim()} onClose={() => router.back()} />;
}
```

- [ ] **Step 2: Run + commit**

Run: `npm test && npm run typecheck`
```bash
git add apps/mobile/app/(doctor)/room
git commit -m "add doctor consultation room screen"
```

---

## Verification (end of Plan 03)

- `cd apps/mobile && npm test && npm run typecheck` — green.
- Device: log in as the seeded demo doctor `+915000000001` → queue shows the six seeded cases, acuity-sorted, emergency with a red left border → open a case → NADI Note + labs render → tap **Start consultation** → the in-app Jitsi room `nadi-<cid>` opens (same room the patient joins) → write a prescription → it now appears on the patient's prescription screen (Plan 02) when the patient polls. Cross-device sync + shared video room confirmed.

**Next plan:** `04-pharmacy-flow` — inbox, order detail, accept/decline + forwarding, then the full 3-phone verification script and the low-end-device smoothness gate. (The richer doctor and pharmacy portals are built in Plans `05-doctor-portal` and `06-pharmacy-portal`.)

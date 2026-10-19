# NADI Frontend — Plan 04: Pharmacy Flow + Final Verification

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Depends on Plans 01–03.**

**Goal:** The pharmacy portal (navy theme) — a live inbox of incoming prescription offers, an order-detail screen to accept or decline (decline auto-forwards to the next consented pharmacy) — and then the full three-phone verification script and the low-end-device smoothness gate that close out the demo build.

**Architecture:** Thin expo-router screens under `app/(pharmacy)/`; network in `src/api/pharmacy.ts`; React Query polling for the inbox. No backend changes — the pharmacy endpoints already exist (`/v1/pharmacy/inbox`, `/offers/{id}/accept`, `/offers/{id}/decline`).

**Tech Stack:** Plan 01–03 stack; `@shopify/flash-list` for the inbox.

## Global Constraints

(Same as Plans 01–03 — repeated for self-containment.)

- TS strict; functional components <150 lines; no logic in route files; tokens only, no inline hex.
- Baseline 360×640; tap targets ≥48dp; primary buttons 56dp; body ≥15.
- No AI/tool attribution; commits short, imperative, lowercase.
- A pharmacy sees the **prescription only — never medical history** (ProjectPlan §11). The inbox/detail render only drugs + patient name, nothing clinical.
- Strictly $0; access token memory / refresh in SecureStore; **every response zod-parsed**.
- Skeletons not spinners; designed empty states.

---

### Task 1: Pharmacy API module

**Files:**
- Create: `apps/mobile/src/api/pharmacy.ts`
- Test: `apps/mobile/src/api/__tests__/pharmacy.test.ts`

**Interfaces:**
- Consumes: `api`, `OfferSchema` (Plan 01 Task 5).
- Produces: `getInbox()` → `Offer[]`; `acceptOffer(id)` → `{ accepted }`; `declineOffer(id)` → `{ declined, forwarded }`.

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/api/__tests__/pharmacy.test.ts`:
```ts
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { getInbox, declineOffer } from '@/api/pharmacy';
import { useSession } from '@/store/session';

const BASE = 'http://test.local';
process.env.EXPO_PUBLIC_API_URL = BASE;
const server = setupServer();
beforeAll(() => server.listen());
beforeEach(() => useSession.setState({ accessToken: 'a', refreshToken: 'r' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

const offer = { id: 'o1', prescriptionId: 'p1', patientName: 'Ramesh', status: 'PENDING',
  lines: [{ drug: 'Para', strength: '500mg', frequency: 'BD', durationDays: 3, notes: null }] };

test('getInbox parses offers', async () => {
  server.use(http.get(`${BASE}/v1/pharmacy/inbox`, () => HttpResponse.json([offer])));
  expect((await getInbox())[0]!.patientName).toBe('Ramesh');
});

test('declineOffer reports forwarding', async () => {
  server.use(http.post(`${BASE}/v1/pharmacy/offers/o1/decline`, () => HttpResponse.json({ declined: true, forwarded: true })));
  expect((await declineOffer('o1')).forwarded).toBe(true);
});
```

- [ ] **Step 2: Run to verify it fails** → `npm test -- api/__tests__/pharmacy` FAIL.

- [ ] **Step 3: Implement**

`apps/mobile/src/api/pharmacy.ts`:
```ts
import { z } from 'zod';
import { api } from '@/api/client';
import { OfferSchema, type Offer } from '@/api/schemas';

export const getInbox = (): Promise<Offer[]> =>
  api.get('/v1/pharmacy/inbox', z.array(OfferSchema));

export const acceptOffer = (id: string) =>
  api.post(`/v1/pharmacy/offers/${id}/accept`, {}, z.object({ accepted: z.boolean() }));

export const declineOffer = (id: string) =>
  api.post(`/v1/pharmacy/offers/${id}/decline`, {}, z.object({ declined: z.boolean(), forwarded: z.boolean() }));
```

- [ ] **Step 4: Run to verify it passes** → `npm test -- api/__tests__/pharmacy` PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/mobile/src/api/pharmacy.ts apps/mobile/src/api/__tests__/pharmacy.test.ts
git commit -m "add pharmacy api module"
```

---

### Task 2: Inbox screen (live)

**Files:**
- Create: `apps/mobile/app/(pharmacy)/index.tsx`
- Create: `apps/mobile/src/features/pharmacy/useInbox.ts`
- Test: `apps/mobile/src/features/pharmacy/__tests__/useInbox.test.tsx`

**Interfaces:**
- Consumes: `getInbox`, `pollInterval`.
- Produces: `useInbox()` polling every 4000 ms; inbox screen as a FlashList of offers with a designed empty state. (The backend returns only `PENDING` offers, so all shown are actionable.)

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/features/pharmacy/__tests__/useInbox.test.tsx`:
```tsx
import { renderHook, waitFor } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useInbox } from '@/features/pharmacy/useInbox';

jest.mock('@/api/pharmacy', () => ({ getInbox: jest.fn(async () => [{ id: 'o1', patientName: 'Ramesh' }]) }));
const wrap = ({ children }: { children: React.ReactNode }) =>
  <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>;

test('loads the inbox', async () => {
  const { result } = renderHook(() => useInbox(), { wrapper: wrap });
  await waitFor(() => expect(result.current.data?.[0]?.patientName).toBe('Ramesh'));
});
```

- [ ] **Step 2: Run to verify it fails** → `npm test -- useInbox` FAIL.

- [ ] **Step 3: Implement the hook**

`apps/mobile/src/features/pharmacy/useInbox.ts`:
```ts
import { useQuery } from '@tanstack/react-query';
import { getInbox } from '@/api/pharmacy';
import { pollInterval } from '@/lib/polling';
export function useInbox() {
  return useQuery({ queryKey: ['inbox'], queryFn: getInbox, refetchInterval: () => pollInterval(true, 4000) });
}
```

- [ ] **Step 4: Build the screen**

`apps/mobile/app/(pharmacy)/index.tsx`:
```tsx
import { Text, View } from 'react-native';
import { FlashList } from '@shopify/flash-list';
import { router } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';
import { Card, EmptyState, ErrorState, Skeleton } from '@/components/ui';
import { useInbox } from '@/features/pharmacy/useInbox';
import type { Offer } from '@/api/schemas';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function PharmacyInbox() {
  const { data, isLoading, isError, refetch } = useInbox();
  const qc = useQueryClient();
  if (isLoading) return <View style={{ padding: spacing.lg, gap: spacing.sm }}>{[0, 1].map((i) => <Skeleton key={i} height={88} />)}</View>;
  if (isError) return <ErrorState message="Could not load the inbox." onRetry={refetch} />;
  return (
    <FlashList data={data ?? []} estimatedItemSize={100} keyExtractor={(o) => o.id}
      contentContainerStyle={{ padding: spacing.lg }}
      ListEmptyComponent={<EmptyState title="No new orders" message="Incoming prescriptions will appear here." />}
      renderItem={({ item }: { item: Offer }) => (
        <View style={{ marginBottom: spacing.sm }}>
          <Card>
            <Text style={{ fontSize: t.body, fontWeight: '700', color: colors.text }}>{item.patientName}</Text>
            <Text style={{ fontSize: t.sm, color: colors.textMuted }}>{item.lines.length} item(s)</Text>
            <Text onPress={() => { qc.setQueryData(['offer', item.id], item);
              router.push({ pathname: '/(pharmacy)/order/[oid]', params: { oid: item.id } }); }}
              style={{ color: colors.navy, fontSize: t.sm, marginTop: spacing.xs }}>View order →</Text>
          </Card>
        </View>
      )} />
  );
}
```

- [ ] **Step 5: Run + commit**

Run: `npm test && npm run typecheck`
```bash
git add apps/mobile/app/(pharmacy)/index.tsx apps/mobile/src/features/pharmacy/useInbox.ts apps/mobile/src/features/pharmacy/__tests__/useInbox.test.tsx
git commit -m "add pharmacy inbox screen"
```

---

### Task 3: Order detail (accept / decline)

**Files:**
- Create: `apps/mobile/app/(pharmacy)/order/[oid].tsx`
- Create: `apps/mobile/src/features/pharmacy/useOfferActions.ts`
- Test: `apps/mobile/src/features/pharmacy/__tests__/useOfferActions.test.ts`

**Interfaces:**
- Consumes: `acceptOffer`, `declineOffer`, the cached `['offer', oid]`.
- Produces: `useOfferActions()` → `{ accept(id), decline(id), pending, result }` where `result` is `'accepted' | 'forwarded' | 'declined' | null`; order screen lists medicines, an Accept and a Decline button, and on completion shows the outcome then returns to the inbox (which re-polls and drops the handled offer).

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/features/pharmacy/__tests__/useOfferActions.test.ts`:
```ts
import { renderHook, act } from '@testing-library/react-native';
import { useOfferActions } from '@/features/pharmacy/useOfferActions';
jest.mock('@/api/pharmacy', () => ({
  acceptOffer: jest.fn(async () => ({ accepted: true })),
  declineOffer: jest.fn(async () => ({ declined: true, forwarded: true })),
}));

test('accept sets result to accepted', async () => {
  const { result } = renderHook(() => useOfferActions());
  await act(async () => { await result.current.accept('o1'); });
  expect(result.current.result).toBe('accepted');
});

test('decline with forwarding sets result to forwarded', async () => {
  const { result } = renderHook(() => useOfferActions());
  await act(async () => { await result.current.decline('o1'); });
  expect(result.current.result).toBe('forwarded');
});
```

- [ ] **Step 2: Run to verify it fails** → `npm test -- useOfferActions` FAIL.

- [ ] **Step 3: Implement the hook**

`apps/mobile/src/features/pharmacy/useOfferActions.ts`:
```ts
import { useState } from 'react';
import { acceptOffer, declineOffer } from '@/api/pharmacy';

type Result = 'accepted' | 'forwarded' | 'declined' | null;

export function useOfferActions() {
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<Result>(null);
  const accept = async (id: string) => {
    setPending(true);
    try { await acceptOffer(id); setResult('accepted'); } finally { setPending(false); }
  };
  const decline = async (id: string) => {
    setPending(true);
    try { const r = await declineOffer(id); setResult(r.forwarded ? 'forwarded' : 'declined'); }
    finally { setPending(false); }
  };
  return { accept, decline, pending, result };
}
```

- [ ] **Step 4: Build the screen**

`apps/mobile/app/(pharmacy)/order/[oid].tsx`:
```tsx
import { useEffect } from 'react';
import { ScrollView, Text, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';
import { Button, Card } from '@/components/ui';
import { useOfferActions } from '@/features/pharmacy/useOfferActions';
import type { Offer } from '@/api/schemas';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function Order() {
  const { oid } = useLocalSearchParams<{ oid: string }>();
  const qc = useQueryClient();
  const offer = qc.getQueryData<Offer>(['offer', oid]);
  const { accept, decline, pending, result } = useOfferActions();
  useEffect(() => {
    if (!result) return;
    const id = setTimeout(() => { void qc.invalidateQueries({ queryKey: ['inbox'] }); router.replace('/(pharmacy)'); }, 1400);
    return () => clearTimeout(id);
  }, [result, qc]);
  if (!offer) return <View style={{ padding: spacing.lg }}><Text style={{ color: colors.textMuted }}>Order not found.</Text></View>;
  if (result) return (
    <View style={{ flex: 1, justifyContent: 'center', padding: spacing.xl }}>
      <Text style={{ fontSize: t.h2, color: colors.navy, fontWeight: '700' }}>
        {result === 'accepted' ? 'Order accepted' : result === 'forwarded' ? 'Declined — forwarded to the next pharmacy' : 'Order declined'}
      </Text>
    </View>
  );
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.h2, fontWeight: '700', color: colors.text }}>Order for {offer.patientName}</Text>
      <Card>{offer.lines.map((l, i) => (
        <Text key={i} style={{ color: colors.text, fontSize: t.sm }}>{l.drug} {l.strength} — {l.frequency}, {l.durationDays}d</Text>
      ))}</Card>
      <Button title="Accept order" color={colors.navy} loading={pending} onPress={() => accept(oid!)} />
      <Button title="Decline" variant="ghost" color={colors.emergency} disabled={pending} onPress={() => decline(oid!)} />
    </ScrollView>
  );
}
```

- [ ] **Step 5: Run + commit**

Run: `npm test && npm run typecheck`
```bash
git add apps/mobile/app/(pharmacy)/order apps/mobile/src/features/pharmacy/useOfferActions.ts apps/mobile/src/features/pharmacy/__tests__/useOfferActions.test.ts
git commit -m "add pharmacy order detail screen"
```

---

### Task 4: Final verification — 3-phone script & low-end smoothness gate

No new code. This task runs the spec's §5 acceptance test and §6 performance gate. Do not mark the demo build "done" until all pass.

**Files:**
- Create: `docs/superpowers/verification/3-phone-script.md` (the runnable checklist, committed so it can be re-run before the demo)

- [ ] **Step 1: Bring up the real stack on the LAN**

```bash
docker compose -f infra/docker-compose.yml up -d --build   # migrates + seeds (ADR-0003)
```
Confirm `GET http://<LAN-IP>:8000/health` returns `{"status":"ok"}` from a phone's browser. Set `apps/mobile/.env` `EXPO_PUBLIC_API_URL=http://<LAN-IP>:8000`. Build the dev client on each phone (MapLibre needs a dev build, not Expo Go): `cd apps/mobile && npx expo run:android`.

- [ ] **Step 2: Write the verification checklist**

Create `docs/superpowers/verification/3-phone-script.md`:
```markdown
# NADI 3-phone demo verification

Phones: A = patient, B = doctor (login +915000000001), C = pharmacy (login +915000020000).

1. [ ] A: new +91 number → OTP 123456 + name → green patient home.
2. [ ] A: enter "chest pain and breathlessness" → Analyzing → RED emergency view with call button. (Back out.)
3. [ ] A: enter "fever and cough", add one report photo → tile shows "Ready" (uploaded to MinIO) → Analyzing → Result with specialty + drivers.
4. [ ] A: doctors list loads; toggle Map → MapLibre map with doctor pins; pick a doctor → slot → Book → Booked.
5. [ ] A → B: within ~4s B's queue shows the new booked patient, acuity-sorted.
6. [ ] A & B: both tap Join/Start consultation → same jit.si room → video connects (camera/mic allowed).
7. [ ] B: open the case → NADI Note (acuity, confidence %, drivers) + labs render → write a prescription → Issue.
8. [ ] B → A: A's prescription screen (was "waiting…") now shows the medicines within ~3s.
9. [ ] A: choose a pharmacy (nothing pre-ticked) → Send → status shows.
10. [ ] A → C: within ~4s C's inbox shows the order → open → Accept.
11. [ ] C → A: A's prescription status flips to ACCEPTED within ~3s.
12. [ ] Repeat 9–11 choosing a closed/declining pharmacy → C declines → "forwarded to the next pharmacy" → the next consented pharmacy receives it.
```
Run every box end to end against the live LAN stack. Fix any failure before proceeding.

- [ ] **Step 3: Low-end device smoothness gate (spec §6)**

On the **cheapest available Android phone** (not the emulator):
- [ ] Scroll the doctor list, doctor queue, and pharmacy inbox — no dropped-frame stutter (target 60fps / 16ms frames; FlashList recycling + expo-image caching should hold this).
- [ ] Navigation transitions and the "analysing" animation stay smooth while a fetch is in flight (Reanimated runs them on the UI thread).
- [ ] Toggle the doctor map — it lazy-mounts without freezing the list.
- [ ] The whole patient → doctor → pharmacy loop completes with no jank, blank screen, or raw spinner.

Record the device model tested in the checklist file.

- [ ] **Step 4: Full test + typecheck gate (spec §5)**

```bash
cd apps/mobile && npm test && npm run typecheck
cd apps/api && .venv/Scripts/python -m pytest
```
All green.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/verification/3-phone-script.md
git commit -m "add 3-phone verification script"
```

---

## Verification (end of Plan 04 — demo build complete)

- `npm test` + `npm run typecheck` (mobile) green; `pytest` (api) green.
- The 3-phone script passes end to end on the real LAN stack.
- The low-end-device smoothness gate passes, device model recorded.

At this point the demo build is complete: all three roles, real backend, real upload, real video, real cross-device sync, MapLibre map, and the performance gate met — all at $0 with no billing account. Remaining project work (trained ML models, Phases 3–5; deployment) is out of scope per the spec and tracked separately ([[nadi-ml-approach]]).

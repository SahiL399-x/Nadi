# NADI Frontend — Plan 06: Pharmacy Portal (v2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Depends on Plans 01–05** (reuses `StatTile`, `NavCard`, `FilterChips`, and the `api.put` client method added in Plan 05).

**Goal:** Build out the "Nadi Pariksha" pharmacy portal on top of the minimal Plan 04 pharmacy flow — a dashboard with the four real order-state counts, a status-filterable orders board, and an order-detail screen that advances an order through the real lifecycle (`PENDING → … → DELIVERED → COMPLETED`) using the backend's validated transitions. The Plan 04 consent inbox (accept/decline + auto-forward) is preserved and moved behind the dashboard.

**Architecture:** The pharmacy portal stays a single themed Stack (navy). This plan **repurposes `(pharmacy)/index.tsx` as the dashboard** (Plan 04 made it the inbox) and **relocates the inbox to `(pharmacy)/inbox.tsx`** — same component, new route. The new orders board and lifecycle detail are stack-pushed routes. Network for the v2 endpoints lives in a new `src/api/pharmacyPortal.ts` beside the existing `src/api/pharmacy.ts`; every response is zod-parsed.

**Tech Stack:** Plan 01–05 stack. No new runtime dependencies.

## Global Constraints

(Same as Plans 01–05 — repeated for self-containment.)

- TS strict; no `any`, no `@ts-ignore`; functional components **<150 lines**; no business logic in route files; **tokens only, no inline hex**.
- Baseline 360×640; tap targets ≥48dp; primary buttons 56dp; body ≥15.
- No AI/tool attribution anywhere; commit messages short, imperative, lowercase.
- **A pharmacy sees the prescription/order only — never medical history** (ProjectPlan §11). Orders render drugs, patient name, phone, counts, totals, status — nothing clinical.
- Strictly $0; access token memory / refresh in SecureStore; **every API response zod-parsed**.
- Skeletons not spinners; every list has a designed empty state.

## Backend contract reference (verified against `apps/api`, do not re-derive)

All under `/v1/pharmacy`; all require the `pharmacy` role.

- `GET /stats` → `{ newOrders, inProgress, outForDelivery, completedToday }` (all `int`).
- `GET /orders?status=all|pending|preparing|verified|to_verify|out_for_delivery|delivered|completed|cancelled|declined|accepted` → `OrderOut[]` `{ id, orderNo, patientName, phone, itemsCount, totalInr, status, placedAt }`. `status` filter is matched case-insensitively against the `OfferStatus` enum; `all` (or omitted) returns every order. An unknown status returns `[]`.
- `POST /orders/{offerId}/status` `{ status }` → `{ status }` (uppercased) on success; **HTTP 400** `"illegal transition"` if the transition is not allowed; **404** if the order is not this pharmacy's.
- Allowed transitions (mirror exactly — the UI must only offer legal next states):

  | From | Allowed next |
  |---|---|
  | `PENDING` | `TO_VERIFY`, `VERIFIED`, `PREPARING`, `CANCELLED` |
  | `ACCEPTED` | `PREPARING`, `CANCELLED` |
  | `TO_VERIFY` | `VERIFIED`, `PREPARING`, `CANCELLED` |
  | `VERIFIED` | `PREPARING`, `CANCELLED` |
  | `PREPARING` | `OUT_FOR_DELIVERY`, `CANCELLED` |
  | `OUT_FOR_DELIVERY` | `DELIVERED`, `CANCELLED` |
  | `DELIVERED` | `COMPLETED` |
  | `COMPLETED` / `CANCELLED` / `DECLINED` | (none — terminal) |

  Advancing to `DELIVERED`/`COMPLETED` also moves the linked prescription to `DELIVERED` server-side (patient sees it update). The existing accept/decline inbox flow (Plan 04) is unchanged.

---

### Task 1: Pharmacy portal API module + zod schemas

**Files:**
- Create: `apps/mobile/src/api/pharmacyPortal.ts`
- Test: `apps/mobile/src/api/__tests__/pharmacyPortal.test.ts`

**Interfaces:**
- Consumes: `api` (Plan 01 Task 7).
- Produces (and exports inferred types):
  - `getPharmacyStats()` → `PharmacyStats`
  - `getOrders(status?: OrderStatusFilter)` → `Order[]`
  - `setOrderStatus(offerId: string, status: string)` → `{ status: string }`
  - `ALLOWED_TRANSITIONS: Record<string, string[]>` and `nextStatuses(current: string): string[]`
  - `STATUS_LABEL: Record<string, string>` for display.

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/api/__tests__/pharmacyPortal.test.ts`:
```ts
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { getPharmacyStats, getOrders, setOrderStatus, nextStatuses } from '@/api/pharmacyPortal';
import { useSession } from '@/store/session';

const BASE = 'http://test.local';
process.env.EXPO_PUBLIC_API_URL = BASE;
const server = setupServer();
beforeAll(() => server.listen());
beforeEach(() => useSession.setState({ accessToken: 'a', refreshToken: 'r' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

test('getPharmacyStats parses the four counts', async () => {
  server.use(http.get(`${BASE}/v1/pharmacy/stats`, () => HttpResponse.json(
    { newOrders: 12, inProgress: 8, outForDelivery: 5, completedToday: 28 })));
  expect((await getPharmacyStats()).completedToday).toBe(28);
});

test('getOrders passes the status filter and parses rows', async () => {
  let seen = '';
  server.use(http.get(`${BASE}/v1/pharmacy/orders`, ({ request }) => {
    seen = new URL(request.url).searchParams.get('status') ?? '';
    return HttpResponse.json([{ id: 'o1', orderNo: 'NP4582', patientName: 'Ramesh', phone: '+91…',
      itemsCount: 3, totalInr: 180, status: 'PREPARING', placedAt: '2026-10-20' }]);
  }));
  const rows = await getOrders('preparing');
  expect(seen).toBe('preparing');
  expect(rows[0]!.orderNo).toBe('NP4582');
});

test('setOrderStatus returns the new status', async () => {
  server.use(http.post(`${BASE}/v1/pharmacy/orders/o1/status`, () => HttpResponse.json({ status: 'OUT_FOR_DELIVERY' })));
  expect((await setOrderStatus('o1', 'OUT_FOR_DELIVERY')).status).toBe('OUT_FOR_DELIVERY');
});

test('nextStatuses mirrors the backend transition map', () => {
  expect(nextStatuses('PREPARING')).toEqual(['OUT_FOR_DELIVERY', 'CANCELLED']);
  expect(nextStatuses('COMPLETED')).toEqual([]);
});
```

- [ ] **Step 2: Run to verify it fails** → `npm test -- pharmacyPortal` FAIL (module not found).

- [ ] **Step 3: Implement**

`apps/mobile/src/api/pharmacyPortal.ts`:
```ts
import { z } from 'zod';
import { api } from '@/api/client';

export const PharmacyStatsSchema = z.object({
  newOrders: z.number(), inProgress: z.number(), outForDelivery: z.number(), completedToday: z.number(),
});
export const OrderSchema = z.object({
  id: z.string(), orderNo: z.string(), patientName: z.string(), phone: z.string(),
  itemsCount: z.number(), totalInr: z.number(), status: z.string(), placedAt: z.string(),
});

export type PharmacyStats = z.infer<typeof PharmacyStatsSchema>;
export type Order = z.infer<typeof OrderSchema>;
export type OrderStatusFilter =
  | 'all' | 'pending' | 'accepted' | 'to_verify' | 'verified' | 'preparing'
  | 'out_for_delivery' | 'delivered' | 'completed' | 'cancelled' | 'declined';

// Mirrors apps/api/app/services/pharmacy_service.py `_ALLOWED` exactly.
export const ALLOWED_TRANSITIONS: Record<string, string[]> = {
  PENDING: ['TO_VERIFY', 'VERIFIED', 'PREPARING', 'CANCELLED'],
  ACCEPTED: ['PREPARING', 'CANCELLED'],
  TO_VERIFY: ['VERIFIED', 'PREPARING', 'CANCELLED'],
  VERIFIED: ['PREPARING', 'CANCELLED'],
  PREPARING: ['OUT_FOR_DELIVERY', 'CANCELLED'],
  OUT_FOR_DELIVERY: ['DELIVERED', 'CANCELLED'],
  DELIVERED: ['COMPLETED'],
  COMPLETED: [],
  CANCELLED: [],
  DECLINED: [],
};
export const nextStatuses = (current: string): string[] => ALLOWED_TRANSITIONS[current] ?? [];

export const STATUS_LABEL: Record<string, string> = {
  PENDING: 'New', ACCEPTED: 'Accepted', TO_VERIFY: 'To verify', VERIFIED: 'Verified',
  PREPARING: 'Preparing', OUT_FOR_DELIVERY: 'Out for delivery', DELIVERED: 'Delivered',
  COMPLETED: 'Completed', CANCELLED: 'Cancelled', DECLINED: 'Declined',
};

export const getPharmacyStats = () => api.get('/v1/pharmacy/stats', PharmacyStatsSchema);

export const getOrders = (status: OrderStatusFilter = 'all'): Promise<Order[]> =>
  api.get(`/v1/pharmacy/orders?status=${status}`, z.array(OrderSchema));

export const setOrderStatus = (offerId: string, status: string) =>
  api.post(`/v1/pharmacy/orders/${offerId}/status`, { status }, z.object({ status: z.string() }));
```

- [ ] **Step 4: Run to verify it passes** → `npm test -- pharmacyPortal` PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/mobile/src/api/pharmacyPortal.ts apps/mobile/src/api/__tests__/pharmacyPortal.test.ts
git commit -m "add pharmacy portal api module"
```

---

### Task 2: Dashboard home + relocate the inbox

**Files:**
- Create: `apps/mobile/app/(pharmacy)/inbox.tsx` (moved Plan 04 inbox)
- Modify: `apps/mobile/app/(pharmacy)/index.tsx` (was the inbox → now the dashboard)
- Create: `apps/mobile/src/features/pharmacy/usePharmacyStats.ts`

**Interfaces:**
- Consumes: `getPharmacyStats`, `pollInterval`, `StatTile`/`NavCard` (Plan 05 Task 3).
- Produces: `usePharmacyStats()` React Query (refetch 8000 ms); the dashboard screen; the inbox now at `/(pharmacy)/inbox`.

- [ ] **Step 1: Move the inbox**

Create `apps/mobile/app/(pharmacy)/inbox.tsx` with the **exact contents** of the current `apps/mobile/app/(pharmacy)/index.tsx` (the Plan 04 inbox — `PharmacyInbox` default export, `useInbox`, FlashList of offers). Rename the component `PharmacyInbox` → `PharmacyInboxScreen`. Its "View order →" still routes to `/(pharmacy)/order/[oid]` (the Plan 04 accept/decline screen) — unchanged.

- [ ] **Step 2: Implement the stats hook**

`apps/mobile/src/features/pharmacy/usePharmacyStats.ts`:
```ts
import { useQuery } from '@tanstack/react-query';
import { getPharmacyStats } from '@/api/pharmacyPortal';
import { pollInterval } from '@/lib/polling';
export function usePharmacyStats() {
  return useQuery({ queryKey: ['pharmacyStats'], queryFn: getPharmacyStats,
    refetchInterval: () => pollInterval(true, 8000) });
}
```

- [ ] **Step 3: Build the dashboard**

Replace `apps/mobile/app/(pharmacy)/index.tsx` entirely:
```tsx
import { ScrollView, Text, View } from 'react-native';
import { router } from 'expo-router';
import { Inbox, ClipboardList } from 'lucide-react-native';
import { StatTile } from '@/components/StatTile';
import { NavCard } from '@/components/NavCard';
import { Skeleton } from '@/components/ui';
import { usePharmacyStats } from '@/features/pharmacy/usePharmacyStats';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function PharmacyDashboard() {
  const { data, isLoading } = usePharmacyStats();
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.h2, fontWeight: '800', color: colors.navy }}>Pharmacy</Text>
      {isLoading || !data ? (
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm }}>
          {[0, 1, 2, 3].map((i) => <View key={i} style={{ width: '47%' }}><Skeleton height={76} /></View>)}
        </View>
      ) : (
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm }}>
          <StatTile label="New Orders" value={data.newOrders} tint={colors.urgent} />
          <StatTile label="In Progress" value={data.inProgress} />
          <StatTile label="Out for Delivery" value={data.outForDelivery} />
          <StatTile label="Completed Today" value={data.completedToday} tint={colors.routine} />
        </View>
      )}
      <Text style={{ fontSize: t.h3, fontWeight: '700', color: colors.text }}>Manage</Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm }}>
        <NavCard label="Orders Board" Icon={ClipboardList} onPress={() => router.push('/(pharmacy)/orders')} />
        <NavCard label="New Requests" Icon={Inbox} onPress={() => router.push('/(pharmacy)/inbox')} />
      </View>
    </ScrollView>
  );
}
```

- [ ] **Step 4: Run + commit**

Run: `npm test && npm run typecheck`
```bash
git add apps/mobile/app/(pharmacy)/index.tsx apps/mobile/app/(pharmacy)/inbox.tsx apps/mobile/src/features/pharmacy/usePharmacyStats.ts
git commit -m "add pharmacy dashboard and relocate inbox"
```

---

### Task 3: Orders board (status-filterable)

**Files:**
- Create: `apps/mobile/app/(pharmacy)/orders.tsx`
- Create: `apps/mobile/src/features/pharmacy/useOrders.ts`
- Create: `apps/mobile/src/components/OrderRow.tsx`
- Test: `apps/mobile/src/features/pharmacy/__tests__/useOrders.test.tsx`

**Interfaces:**
- Consumes: `getOrders`, `pollInterval`, `STATUS_LABEL`, `FilterChips` (Plan 05 Task 7).
- Produces: `useOrders(status)` React Query (refetch 5000 ms); `OrderRow({ order, onPress })` showing orderNo, patient, item count, total, and a status label; the orders screen with filter chips + FlashList + empty state.

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/features/pharmacy/__tests__/useOrders.test.tsx`:
```tsx
import { renderHook, waitFor } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useOrders } from '@/features/pharmacy/useOrders';

jest.mock('@/api/pharmacyPortal', () => ({
  getOrders: jest.fn(async () => [{ id: 'o1', orderNo: 'NP4582', patientName: 'Ramesh', phone: 'x',
    itemsCount: 3, totalInr: 180, status: 'PREPARING', placedAt: '2026-10-20' }]),
}));
const wrap = ({ children }: { children: React.ReactNode }) =>
  <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>;

test('loads orders', async () => {
  const { result } = renderHook(() => useOrders('all'), { wrapper: wrap });
  await waitFor(() => expect(result.current.data?.[0]?.orderNo).toBe('NP4582'));
});
```

- [ ] **Step 2: Run to verify it fails** → `npm test -- useOrders` FAIL.

- [ ] **Step 3: Implement the hook + row**

`apps/mobile/src/features/pharmacy/useOrders.ts`:
```ts
import { useQuery } from '@tanstack/react-query';
import { getOrders, type OrderStatusFilter } from '@/api/pharmacyPortal';
import { pollInterval } from '@/lib/polling';
export function useOrders(status: OrderStatusFilter) {
  return useQuery({ queryKey: ['orders', status], queryFn: () => getOrders(status),
    refetchInterval: () => pollInterval(true, 5000) });
}
```

`apps/mobile/src/components/OrderRow.tsx`:
```tsx
import { Pressable, Text, View } from 'react-native';
import { Card } from '@/components/ui';
import type { Order } from '@/api/pharmacyPortal';
import { STATUS_LABEL } from '@/api/pharmacyPortal';
import { colors, spacing, type as t } from '@/theme/tokens';

export function OrderRow({ order, onPress }: { order: Order; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} style={{ marginBottom: spacing.sm }}>
      <Card>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
          <Text style={{ fontSize: t.body, fontWeight: '800', color: colors.navy }}>{order.orderNo}</Text>
          <Text style={{ fontSize: t.xs, color: colors.navy, fontWeight: '700' }}>
            {STATUS_LABEL[order.status] ?? order.status}
          </Text>
        </View>
        <Text style={{ fontSize: t.sm, color: colors.text }}>{order.patientName}</Text>
        <Text style={{ fontSize: t.sm, color: colors.textMuted }}>
          {order.itemsCount} item(s) · ₹{order.totalInr}
        </Text>
      </Card>
    </Pressable>
  );
}
```

- [ ] **Step 4: Run to verify it passes** → `npm test -- useOrders` PASS.

- [ ] **Step 5: Build the orders screen**

`apps/mobile/app/(pharmacy)/orders.tsx`:
```tsx
import { useState } from 'react';
import { View } from 'react-native';
import { FlashList } from '@shopify/flash-list';
import { router } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';
import { EmptyState, ErrorState, Skeleton } from '@/components/ui';
import { FilterChips } from '@/components/FilterChips';
import { OrderRow } from '@/components/OrderRow';
import { useOrders } from '@/features/pharmacy/useOrders';
import type { OrderStatusFilter } from '@/api/pharmacyPortal';
import { spacing } from '@/theme/tokens';

const OPTS = [
  { label: 'All', value: 'all' }, { label: 'New', value: 'pending' },
  { label: 'Preparing', value: 'preparing' }, { label: 'Out for delivery', value: 'out_for_delivery' },
  { label: 'Delivered', value: 'delivered' }, { label: 'Completed', value: 'completed' },
];

export default function Orders() {
  const [status, setStatus] = useState<OrderStatusFilter>('all');
  const { data, isLoading, isError, refetch } = useOrders(status);
  const qc = useQueryClient();
  return (
    <View style={{ flex: 1, paddingTop: spacing.lg, gap: spacing.sm }}>
      <FilterChips options={OPTS} value={status} onChange={(v) => setStatus(v as OrderStatusFilter)} />
      {isLoading ? (
        <View style={{ padding: spacing.lg, gap: spacing.sm }}>{[0, 1, 2].map((i) => <Skeleton key={i} height={84} />)}</View>
      ) : isError ? <ErrorState message="Could not load orders." onRetry={refetch} /> : (
        <FlashList data={data ?? []} estimatedItemSize={96} keyExtractor={(o) => o.id}
          contentContainerStyle={{ padding: spacing.lg }}
          ListEmptyComponent={<EmptyState title="No orders" message="Orders in this state will appear here." />}
          renderItem={({ item }) => (
            <OrderRow order={item} onPress={() => {
              qc.setQueryData(['orderDetail', item.id], item);
              router.push({ pathname: '/(pharmacy)/orders/[oid]', params: { oid: item.id } });
            }} />
          )} />
      )}
    </View>
  );
}
```

- [ ] **Step 6: Run + commit**

Run: `npm test && npm run typecheck`
```bash
git add apps/mobile/app/(pharmacy)/orders.tsx apps/mobile/src/features/pharmacy/useOrders.ts apps/mobile/src/components/OrderRow.tsx apps/mobile/src/features/pharmacy/__tests__/useOrders.test.tsx
git commit -m "add pharmacy orders board"
```

---

### Task 4: Order lifecycle detail (validated transitions)

The detail screen reads the order cached by the board (`['orderDetail', oid]`), shows its fields, and offers **only the legal next statuses** for the current state (from `nextStatuses`). Tapping a transition calls the backend; on success the on-screen status updates so the pharmacist can advance step-by-step (Preparing → Out for delivery → Delivered → Completed) without leaving; the orders list is invalidated so the board reflects the change.

**Files:**
- Create: `apps/mobile/app/(pharmacy)/orders/[oid].tsx`
- Create: `apps/mobile/src/features/pharmacy/useOrderTransition.ts`
- Test: `apps/mobile/src/features/pharmacy/__tests__/useOrderTransition.test.ts`

**Interfaces:**
- Consumes: `setOrderStatus`, `nextStatuses`, `STATUS_LABEL`, cached `['orderDetail', oid]`.
- Produces: `useOrderTransition()` → `{ advance(offerId, status), pending, error }` where `error` is set to a human message on an illegal transition (HTTP 400) and cleared on success; the order-detail screen.

- [ ] **Step 1: Write the failing test**

`apps/mobile/src/features/pharmacy/__tests__/useOrderTransition.test.ts`:
```ts
import { renderHook, act } from '@testing-library/react-native';
import { useOrderTransition } from '@/features/pharmacy/useOrderTransition';

jest.mock('@/api/pharmacyPortal', () => ({
  setOrderStatus: jest.fn(async (_id: string, status: string) => {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    if (status === 'DELIVERED') throw new (require('@/api/client').ApiError)(400, 'illegal transition');
    return { status };
  }),
}));

test('advance returns the new status on success', async () => {
  const { result } = renderHook(() => useOrderTransition());
  let out = '';
  await act(async () => { out = await result.current.advance('o1', 'PREPARING'); });
  expect(out).toBe('PREPARING');
  expect(result.current.error).toBeNull();
});

test('an illegal transition sets a human error and does not throw', async () => {
  const { result } = renderHook(() => useOrderTransition());
  await act(async () => { await result.current.advance('o1', 'DELIVERED'); });
  expect(result.current.error).toMatch(/could not/i);
});
```
(The hook treats any thrown error the same, so the test only needs `setOrderStatus` to reject for an illegal target.)

- [ ] **Step 2: Run to verify it fails** → `npm test -- useOrderTransition` FAIL.

- [ ] **Step 3: Implement the hook**

`apps/mobile/src/features/pharmacy/useOrderTransition.ts`:
```ts
import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { setOrderStatus } from '@/api/pharmacyPortal';

export function useOrderTransition() {
  const qc = useQueryClient();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const advance = async (offerId: string, status: string): Promise<string> => {
    setPending(true); setError(null);
    try {
      const r = await setOrderStatus(offerId, status);
      await qc.invalidateQueries({ queryKey: ['orders'] });
      await qc.invalidateQueries({ queryKey: ['pharmacyStats'] });
      return r.status;
    } catch {
      setError('Could not update this order. Please try again.');
      return '';
    } finally { setPending(false); }
  };
  return { advance, pending, error };
}
```

- [ ] **Step 4: Run to verify it passes** → `npm test -- useOrderTransition` PASS.

- [ ] **Step 5: Build the detail screen**

`apps/mobile/app/(pharmacy)/orders/[oid].tsx`:
```tsx
import { useState } from 'react';
import { ScrollView, Text, View } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';
import { Button, Card } from '@/components/ui';
import { useOrderTransition } from '@/features/pharmacy/useOrderTransition';
import { nextStatuses, STATUS_LABEL, type Order } from '@/api/pharmacyPortal';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function OrderDetail() {
  const { oid } = useLocalSearchParams<{ oid: string }>();
  const qc = useQueryClient();
  const cached = qc.getQueryData<Order>(['orderDetail', oid]);
  const [status, setStatus] = useState<string>(cached?.status ?? '');
  const { advance, pending, error } = useOrderTransition();
  if (!cached) return <View style={{ padding: spacing.lg }}><Text style={{ color: colors.textMuted }}>Order not found.</Text></View>;
  const options = nextStatuses(status);
  const go = async (next: string) => { const ok = await advance(oid!, next); if (ok) setStatus(ok); };
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.h2, fontWeight: '800', color: colors.navy }}>{cached.orderNo}</Text>
      <Card>
        <Text style={{ fontSize: t.body, fontWeight: '700', color: colors.text }}>{cached.patientName}</Text>
        <Text style={{ fontSize: t.sm, color: colors.textMuted }}>{cached.phone}</Text>
        <Text style={{ fontSize: t.sm, color: colors.text }}>{cached.itemsCount} item(s) · ₹{cached.totalInr}</Text>
        <Text style={{ fontSize: t.sm, color: colors.navy, fontWeight: '700', marginTop: spacing.xs }}>
          Status: {STATUS_LABEL[status] ?? status}
        </Text>
      </Card>
      {error ? <Text style={{ color: colors.emergency, fontSize: t.sm }}>{error}</Text> : null}
      {options.length === 0 ? (
        <Text style={{ fontSize: t.sm, color: colors.textMuted }}>This order is complete — no further action.</Text>
      ) : options.map((next) => (
        <Button key={next} title={`Mark ${STATUS_LABEL[next] ?? next}`} loading={pending}
          color={next === 'CANCELLED' ? colors.emergency : colors.navy}
          variant={next === 'CANCELLED' ? 'ghost' : 'primary'}
          onPress={() => go(next)} />
      ))}
    </ScrollView>
  );
}
```

- [ ] **Step 6: Run + commit**

Run: `npm test && npm run typecheck`
```bash
git add apps/mobile/app/(pharmacy)/orders apps/mobile/src/features/pharmacy/useOrderTransition.ts apps/mobile/src/features/pharmacy/__tests__/useOrderTransition.test.ts
git commit -m "add pharmacy order lifecycle detail"
```

---

## Verification (end of Plan 06)

- `cd apps/mobile && npm test && npm run typecheck` — green.
- Device, logged in as the seeded pharmacy `+915000020000`:
  - Dashboard shows the seeded counts (New 12 / In Progress 8 / Out for Delivery 5 / Completed 28, per the demo seed targets).
  - Orders board lists orders; filter chips (New / Preparing / Out for delivery / Delivered / Completed) re-query and update the list.
  - Opening an order shows only the legal next statuses; advancing Preparing → Out for delivery → Delivered → Completed works step-by-step; the board and dashboard counts update on return (polling).
  - Advancing to Delivered flips the patient's prescription status (cross-device: the patient's prescription screen shows DELIVERED).
  - The Plan 04 consent inbox still works from the "New Requests" card (accept / decline → "forwarded to the next pharmacy").

**Next:** the Jitsi in-app video swap is folded into Plans 02 and 03 (see those plans' amended video tasks). After Plans 01–06 execute, run Plan 04 Task 4's 3-phone verification script + low-end smoothness gate to close out the demo build.

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

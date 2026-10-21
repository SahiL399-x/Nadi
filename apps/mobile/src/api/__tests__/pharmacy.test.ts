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

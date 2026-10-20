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

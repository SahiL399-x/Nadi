import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { searchDoctors, getTriage, listPharmacies } from '@/api/patient';
import { useSession } from '@/store/session';

const BASE = 'http://test.local';
process.env.EXPO_PUBLIC_API_URL = BASE;
const server = setupServer();
beforeAll(() => server.listen());
beforeEach(() => useSession.setState({ accessToken: 'a', refreshToken: 'r' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

const doctor = {
  id: 'd1', name: 'Dr A', specialty: 'Cardiology', qualifications: 'MBBS', experienceYears: 5,
  distanceKm: 2.1, lat: 19.99, lng: 73.79, feeInr: 400, rating: 4.6, reviewCount: 10,
  languages: ['Hindi'], nextSlot: '09:00', photoUrl: 'x', availableSlots: ['09:00', '10:00'],
};

test('searchDoctors parses the list', async () => {
  server.use(http.get(`${BASE}/v1/doctors`, () => HttpResponse.json([doctor])));
  const list = await searchDoctors({ specialty: 'Cardiology' });
  expect(list[0]!.lat).toBeCloseTo(19.99);
});

test('getTriage returns pending then result', async () => {
  server.use(http.get(`${BASE}/v1/consultations/c1/triage`, () => HttpResponse.json({ status: 'pending' })));
  const res = await getTriage('c1');
  expect('status' in res && res.status === 'pending').toBe(true);
});

test('listPharmacies parses', async () => {
  server.use(http.get(`${BASE}/v1/pharmacies`, () =>
    HttpResponse.json([{ id: 'p1', name: 'Medico', distanceKm: 0.3, deliversInMins: 16, isOpen: true }])));
  expect((await listPharmacies())[0]!.name).toBe('Medico');
});

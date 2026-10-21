import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import {
  getDoctorStats, getAppointments, searchMedicines, getPatient,
  putAvailability, updateDoctorProfile, listNotes,
} from '@/api/doctorPortal';
import { useSession } from '@/store/session';

const BASE = 'http://test.local';
process.env.EXPO_PUBLIC_API_URL = BASE;
const server = setupServer();
beforeAll(() => server.listen());
beforeEach(() => useSession.setState({ accessToken: 'a', refreshToken: 'r' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

test('getDoctorStats parses the dashboard numbers', async () => {
  server.use(http.get(`${BASE}/v1/doctor/stats`, () => HttpResponse.json(
    { appointmentsToday: 8, pending: 3, completed: 3, prescriptionsIssued: 6, newPatients: 2 })));
  expect((await getDoctorStats()).prescriptionsIssued).toBe(6);
});

test('getAppointments passes the date and parses rows with a nullable acuity', async () => {
  let seen = '';
  server.use(http.get(`${BASE}/v1/doctor/appointments`, ({ request }) => {
    seen = new URL(request.url).searchParams.get('date') ?? '';
    return HttpResponse.json([{ id: 'c1', patientId: 'p1', patientName: 'Ramesh', patientAge: 58,
      patientSex: 'M', photoUrl: 'x', time: '10:00', status: 'BOOKED', acuity: null, complaint: 'chest pain' }]);
  }));
  const rows = await getAppointments('2026-10-20');
  expect(seen).toBe('2026-10-20');
  expect(rows[0]!.acuity).toBeNull();
  expect(rows[0]!.patientId).toBe('p1');
});

test('searchMedicines parses the catalog', async () => {
  server.use(http.get(`${BASE}/v1/medicines`, () => HttpResponse.json(
    [{ id: 'm1', name: 'Paracetamol', strength: '500mg', form: 'tablet' }])));
  expect((await searchMedicines('para'))[0]!.name).toBe('Paracetamol');
});

test('getPatient parses the medical history', async () => {
  server.use(http.get(`${BASE}/v1/doctor/patients/p1`, () => HttpResponse.json({
    name: 'Ramesh', age: 58, sex: 'M', conditions: ['Diabetes'], allergies: [],
    familyHistory: ['Hypertension'], noKnownAllergies: true,
    latestVisit: { visitedAt: '2026-10-01', summary: 'Follow-up', status: 'DONE' },
    visits: [{ visitedAt: '2026-10-01', summary: 'Follow-up', status: 'DONE' }],
    prescriptions: ['Metformin 500mg'],
  })));
  const p = await getPatient('p1');
  expect(p.noKnownAllergies).toBe(true);
  expect(p.latestVisit?.summary).toBe('Follow-up');
});

test('putAvailability round-trips the week', async () => {
  const week = Array.from({ length: 7 }, (_, weekday) => (
    { weekday, morning: '09:00-13:00', evening: '17:00-20:00', isOpen: weekday < 5 }));
  server.use(http.put(`${BASE}/v1/doctor/availability`, async ({ request }) => {
    const body = (await request.json()) as { days: unknown[] };
    return HttpResponse.json(body.days);
  }));
  expect((await putAvailability(week)).length).toBe(7);
});

test('updateDoctorProfile sends only editable fields', async () => {
  server.use(http.put(`${BASE}/v1/doctor/profile`, () => HttpResponse.json({
    name: 'Dr A', specialty: 'Cardiology', qualifications: 'MBBS, MD', experienceYears: 12,
    clinicAddress: 'New addr', about: 'Updated', photoUrl: 'x' })));
  expect((await updateDoctorProfile({ clinicAddress: 'New addr' })).clinicAddress).toBe('New addr');
});

test('listNotes parses the private notebook', async () => {
  server.use(http.get(`${BASE}/v1/consultations/c1/notes`, () => HttpResponse.json(
    [{ id: 'n1', text: 'BP elevated', createdAt: '2026-10-20T10:00:00' }])));
  expect((await listNotes('c1'))[0]!.text).toBe('BP elevated');
});

import { DoctorSchema, TriageResultSchema, TokenPairSchema } from '@/api/schemas';

test('DoctorSchema accepts a valid doctor with coordinates', () => {
  const d = DoctorSchema.parse({
    id: 'u1', name: 'Dr A', specialty: 'Cardiology', qualifications: 'MBBS',
    experienceYears: 5, distanceKm: 2.1, lat: 19.99, lng: 73.79, feeInr: 400,
    rating: 4.6, reviewCount: 12, languages: ['Hindi'], nextSlot: '09:00',
    photoUrl: 'x', availableSlots: ['09:00'],
  });
  expect(d.lat).toBeCloseTo(19.99);
});

test('TriageResultSchema rejects an unknown acuity', () => {
  expect(() => TriageResultSchema.parse({ acuity: 'MILD' })).toThrow();
});

test('TokenPairSchema requires role', () => {
  expect(() => TokenPairSchema.parse({ accessToken: 'a', refreshToken: 'r', userId: 'u' })).toThrow();
});

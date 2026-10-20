import { SPECIALTIES } from '@/features/patient/specialties';

test('maps display labels to backend specialty strings used in the seed', () => {
  const byLabel = Object.fromEntries(SPECIALTIES.map((s) => [s.label, s.specialty]));
  expect(byLabel["Women's Health"]).toBe('Gynaecology');
  expect(byLabel['Skin Specialist']).toBe('Dermatology');
  expect(byLabel['Heart']).toBe('Cardiology');
});

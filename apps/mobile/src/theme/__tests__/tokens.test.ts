import { colors, acuityColor, roleTheme } from '@/theme/tokens';
import { roleTheme as _r } from '@/theme/roles';

test('acuity scale is the medical colour-blind-safe scale', () => {
  expect(acuityColor('ROUTINE')).toBe('#15803D');
  expect(acuityColor('PRIORITY')).toBe('#CA8A04');
  expect(acuityColor('URGENT')).toBe('#EA580C');
  expect(acuityColor('EMERGENCY')).toBe('#B91C1C');
});

test('role themes: patient green, doctor navy, pharmacy orange', () => {
  expect(roleTheme('patient').primary).toBe('#22B24C');
  expect(roleTheme('doctor').primary).toBe('#003366');
  expect(roleTheme('pharmacy').primary).toBe('#F97316');
});

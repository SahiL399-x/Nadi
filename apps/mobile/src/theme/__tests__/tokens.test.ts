import { colors, acuityColor, roleTheme } from '@/theme/tokens';
import { roleTheme as _r } from '@/theme/roles';

test('acuity scale is the medical colour-blind-safe scale', () => {
  expect(acuityColor('ROUTINE')).toBe('#15803D');
  expect(acuityColor('PRIORITY')).toBe('#CA8A04');
  expect(acuityColor('URGENT')).toBe('#EA580C');
  expect(acuityColor('EMERGENCY')).toBe('#B91C1C');
});

test('patient theme is green, doctor/pharmacy navy', () => {
  expect(roleTheme('patient').primary).toBe('#2E8B57');
  expect(roleTheme('doctor').primary).toBe('#003366');
  expect(roleTheme('pharmacy').primary).toBe('#003366');
});

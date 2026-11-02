import { roleTheme } from '@/theme/tokens';
import { roleTheme as _r } from '@/theme/roles';

test('role themes: patient green, doctor navy, pharmacy orange', () => {
  expect(roleTheme('patient').primary).toBe('#22B24C');
  expect(roleTheme('doctor').primary).toBe('#003366');
  expect(roleTheme('pharmacy').primary).toBe('#F97316');
});

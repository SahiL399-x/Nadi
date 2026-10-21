import { isoDate } from '@/lib/dates';

test('isoDate formats as YYYY-MM-DD', () => {
  expect(isoDate(new Date('2026-10-20T09:30:00'))).toBe('2026-10-20');
});

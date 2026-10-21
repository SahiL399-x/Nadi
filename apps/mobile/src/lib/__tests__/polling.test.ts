import { pollInterval } from '@/lib/polling';

test('returns the interval when active', () => {
  expect(pollInterval(true, 1500)).toBe(1500);
});
test('returns false (paused) when inactive', () => {
  expect(pollInterval(false, 1500)).toBe(false);
});

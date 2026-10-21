import { renderHook, act } from '@testing-library/react-native';
import { useBook } from '@/features/patient/useBook';

jest.mock('@/api/patient', () => ({ book: jest.fn(async () => ({ booked: true })) }));

test('confirm resolves true', async () => {
  // this installed @testing-library/react-native version's renderHook is async (matches
  // its render()), unlike the brief's sync snippet — awaited here to get a populated result.
  const { result } = await renderHook(() => useBook());
  let ok = false;
  await act(async () => { ok = await result.current.confirm('c1', 'd1', '09:00'); });
  expect(ok).toBe(true);
});

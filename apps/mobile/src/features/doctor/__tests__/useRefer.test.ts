import { renderHook, act } from '@testing-library/react-native';
import { useRefer } from '@/features/doctor/useRefer';
jest.mock('@/api/doctor', () => ({ refer: jest.fn(async () => ({ referred: true })) }));

test('submit resolves true', async () => {
  const { result } = await renderHook(() => useRefer());
  let ok = false;
  await act(async () => { ok = await result.current.submit('c1', 'Cardiology', 'needs ECG'); });
  expect(ok).toBe(true);
});

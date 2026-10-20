import { renderHook, act } from '@testing-library/react-native';
import { usePrescribe } from '@/features/doctor/usePrescribe';
jest.mock('@/api/doctor', () => ({ prescribe: jest.fn(async () => ({ prescriptionId: 'p1' })) }));

test('submit returns the prescription id', async () => {
  const { result } = await renderHook(() => usePrescribe());
  let id = '';
  await act(async () => { id = await result.current.submit('c1', [{ drug: 'Para', strength: '500mg', frequency: 'BD', durationDays: 3 }]); });
  expect(id).toBe('p1');
});

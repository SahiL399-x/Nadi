import { renderHook, act } from '@testing-library/react-native';
import { useIntake } from '@/features/patient/useIntake';

jest.mock('@/api/patient', () => ({ intake: jest.fn(async () => ({ consultationId: 'c1', jobId: 'j1' })) }));

test('submit returns a consultation id', async () => {
  // this installed @testing-library/react-native version's renderHook is async (matches
  // its render()), unlike the brief's sync snippet — awaited here to get a populated result.
  const { result } = await renderHook(() => useIntake());
  let id = '';
  await act(async () => { id = await result.current.submit({ symptomText: 'fever', reportImageUris: [], lang: 'en' }); });
  expect(id).toBe('c1');
});

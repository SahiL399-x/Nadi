import { renderHook, act } from '@testing-library/react-native';
import { useOfferActions } from '@/features/pharmacy/useOfferActions';
jest.mock('@/api/pharmacy', () => ({
  acceptOffer: jest.fn(async () => ({ accepted: true })),
  declineOffer: jest.fn(async () => ({ declined: true, forwarded: true })),
}));

test('accept sets result to accepted', async () => {
  const { result } = await renderHook(() => useOfferActions());
  await act(async () => { await result.current.accept('o1'); });
  expect(result.current.result).toBe('accepted');
});

test('decline with forwarding sets result to forwarded', async () => {
  const { result } = await renderHook(() => useOfferActions());
  await act(async () => { await result.current.decline('o1'); });
  expect(result.current.result).toBe('forwarded');
});

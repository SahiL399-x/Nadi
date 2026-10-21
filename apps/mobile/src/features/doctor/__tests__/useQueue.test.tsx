import { renderHook, waitFor } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useQueue } from '@/features/doctor/useQueue';

jest.mock('@/api/doctor', () => ({ getQueue: jest.fn(async () => [{ id: 'q1', patientName: 'Ramesh', acuity: 'URGENT' }]) }));
const wrap = ({ children }: { children: React.ReactNode }) =>
  <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>;

test('loads the queue', async () => {
  const { result } = await renderHook(() => useQueue(), { wrapper: wrap });
  await waitFor(() => expect(result.current.data?.[0]?.patientName).toBe('Ramesh'));
});

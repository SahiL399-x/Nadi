import { renderHook, waitFor } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useInbox } from '@/features/pharmacy/useInbox';

jest.mock('@/api/pharmacy', () => ({ getInbox: jest.fn(async () => [{ id: 'o1', patientName: 'Ramesh' }]) }));
const wrap = ({ children }: { children: React.ReactNode }) =>
  <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>;

test('loads the inbox', async () => {
  const { result } = await renderHook(() => useInbox(), { wrapper: wrap });
  await waitFor(() => expect(result.current.data?.[0]?.patientName).toBe('Ramesh'));
});

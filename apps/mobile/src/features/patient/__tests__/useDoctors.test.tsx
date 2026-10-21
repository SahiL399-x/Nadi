import { renderHook, waitFor } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useDoctors } from '@/features/patient/useDoctors';

jest.mock('@/api/patient', () => ({ searchDoctors: jest.fn(async () => [{ id: 'd1', name: 'Dr A' }]) }));
const wrap = ({ children }: { children: React.ReactNode }) =>
  <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>;

test('loads doctors', async () => {
  const { result } = await renderHook(() => useDoctors('Cardiology'), { wrapper: wrap });
  await waitFor(() => expect(result.current.data?.[0]?.name).toBe('Dr A'));
});

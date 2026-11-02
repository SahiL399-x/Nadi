import { renderHook, waitFor } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useTriage } from '@/features/patient/useTriage';

jest.mock('@/api/patient', () => ({
  getTriage: jest.fn(async () => ({
    specialties: [{ name: 'Cardiology', score: 0.8 }], labs: [], modelVersion: 'stub',
  })),
}));

const wrap = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>
);

test('resolves to a triage result', async () => {
  const { result } = await renderHook(() => useTriage('c1'), { wrapper: wrap });
  await waitFor(() => expect(result.current.data?.specialties[0]?.name).toBe('Cardiology'));
});

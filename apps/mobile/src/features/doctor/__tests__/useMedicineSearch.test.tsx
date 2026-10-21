import { renderHook, waitFor } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useMedicineSearch } from '@/features/doctor/useMedicineSearch';

jest.mock('@/api/doctorPortal', () => ({
  searchMedicines: jest.fn(async (q?: string) =>
    (q === 'amox' ? [{ id: 'm2', name: 'Amoxicillin', strength: '500mg', form: 'capsule' }] : [])),
}));

const wrap = ({ children }: { children: React.ReactNode }) =>
  <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>;

test('returns matches for the query', async () => {
  const { result } = await renderHook(() => useMedicineSearch('amox'), { wrapper: wrap });
  await waitFor(() => expect(result.current.data?.[0]?.name).toBe('Amoxicillin'));
});

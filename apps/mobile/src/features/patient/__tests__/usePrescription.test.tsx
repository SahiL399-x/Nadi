import { renderHook, waitFor } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { usePrescription } from '@/features/patient/usePrescription';

jest.mock('@/api/patient', () => ({
  getConsultation: jest.fn(async () => ({ id: 'c1', status: 'BOOKED', prescriptionId: 'p1' })),
  getPrescription: jest.fn(async () => ({ id: 'p1', patientName: 'X', doctorName: 'Dr', issuedAt: 't',
    lines: [{ drug: 'Paracetamol', strength: '500mg', frequency: 'BD', durationDays: 3, notes: null }], status: 'PENDING' })),
}));
const wrap = ({ children }: { children: React.ReactNode }) =>
  <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>;

test('discovers prescription id then loads the prescription', async () => {
  // this installed @testing-library/react-native version's renderHook is async (matches
  // its render()), unlike the brief's sync snippet — awaited here to get a populated result.
  const { result } = await renderHook(() => usePrescription('c1'), { wrapper: wrap });
  await waitFor(() => expect(result.current.prescription?.lines[0]?.drug).toBe('Paracetamol'));
});

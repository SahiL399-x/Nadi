import React from 'react';
import { renderHook, waitFor } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useOrders } from '@/features/pharmacy/useOrders';

jest.mock('@/api/pharmacyPortal', () => ({
  getOrders: jest.fn(async () => [{ id: 'o1', orderNo: 'NP4582', patientName: 'Ramesh', phone: 'x',
    itemsCount: 3, totalInr: 180, status: 'PREPARING', placedAt: '2026-10-20' }]),
}));
const wrap = ({ children }: { children: React.ReactNode }) =>
  <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>;

test('loads orders', async () => {
  const { result } = await renderHook(() => useOrders('all'), { wrapper: wrap });
  await waitFor(() => expect(result.current.data?.[0]?.orderNo).toBe('NP4582'));
});

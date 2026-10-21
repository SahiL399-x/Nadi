import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAvailability } from '@/features/doctor/useAvailability';

jest.mock('@/api/doctorPortal', () => ({
  getAvailability: jest.fn(async () =>
    Array.from({ length: 7 }, (_, weekday) =>
      ({ weekday, morning: '09:00-13:00', evening: '17:00-20:00', isOpen: weekday < 5 }))),
  putAvailability: jest.fn(async (days: unknown) => days),
}));

const wrap = ({ children }: { children: React.ReactNode }) =>
  <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>;

test('toggle flips a day open flag', async () => {
  const { result } = await renderHook(() => useAvailability(), { wrapper: wrap });
  await waitFor(() => expect(result.current.week.length).toBe(7));
  await act(async () => { result.current.toggle(5); });
  expect(result.current.week[5]!.isOpen).toBe(true);
});

import React from 'react';
import { renderHook, act } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useOrderTransition } from '@/features/pharmacy/useOrderTransition';

jest.mock('@/api/pharmacyPortal', () => ({
  setOrderStatus: jest.fn(async (_id: string, status: string) => {
    if (status === 'DELIVERED') throw new (require('@/api/client').ApiError)(400, 'illegal transition');
    return { status };
  }),
}));

const wrap = ({ children }: { children: React.ReactNode }) =>
  React.createElement(QueryClientProvider, { client: new QueryClient() }, children);

test('advance returns the new status on success', async () => {
  const { result } = await renderHook(() => useOrderTransition(), { wrapper: wrap });
  let out = '';
  await act(async () => { out = await result.current.advance('o1', 'PREPARING'); });
  expect(out).toBe('PREPARING');
  expect(result.current.error).toBeNull();
});

test('an illegal transition sets a human error and does not throw', async () => {
  const { result } = await renderHook(() => useOrderTransition(), { wrapper: wrap });
  await act(async () => { await result.current.advance('o1', 'DELIVERED'); });
  expect(result.current.error).toMatch(/could not/i);
});

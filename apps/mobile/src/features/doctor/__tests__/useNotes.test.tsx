import { renderHook, act, waitFor } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useNotes } from '@/features/doctor/useNotes';

jest.mock('@/api/doctorPortal', () => {
  const store: { id: string; text: string; createdAt: string }[] = [];
  return {
    listNotes: jest.fn(async () => [...store]),
    addNote: jest.fn(async (_c: string, text: string) => {
      store.push({ id: `n${store.length}`, text, createdAt: '2026-10-20T10:00:00' });
      return { id: `n${store.length - 1}` };
    }),
  };
});

const wrap = ({ children }: { children: React.ReactNode }) =>
  <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>;

test('adds a note and the list reflects it', async () => {
  const { result } = await renderHook(() => useNotes('c1'), { wrapper: wrap });
  await act(async () => { await result.current.add('BP elevated'); });
  await waitFor(() => expect(result.current.notes.some((n) => n.text === 'BP elevated')).toBe(true));
});

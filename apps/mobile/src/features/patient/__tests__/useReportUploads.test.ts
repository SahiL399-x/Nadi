import { renderHook, act, waitFor } from '@testing-library/react-native';
import { useReportUploads } from '@/features/patient/useReportUploads';

jest.mock('@/lib/upload', () => ({
  uploadReport: jest.fn(async (uri: string) => (uri.includes('bad') ? Promise.reject(new Error('x')) : 'key-ok')),
  UploadError: class extends Error {},
}));

test('a successful upload becomes done with an object key', async () => {
  // this installed @testing-library/react-native version's renderHook is async (matches
  // its render()), unlike the brief's sync snippet — awaited here to get a populated result.
  const { result } = await renderHook(() => useReportUploads());
  await act(() => { result.current.add('file://good.jpg', 'image', 'upload'); });
  await waitFor(() => expect(result.current.items[0]!.status).toBe('done'));
  expect(result.current.objectKeys).toEqual(['key-ok']);
  expect(result.current.allSettled).toBe(true);
});

test('a failed upload is error and blocks allSettled', async () => {
  const { result } = await renderHook(() => useReportUploads());
  await act(() => { result.current.add('file://bad.jpg', 'image', 'upload'); });
  await waitFor(() => expect(result.current.items[0]!.status).toBe('error'));
  expect(result.current.allSettled).toBe(false);
});

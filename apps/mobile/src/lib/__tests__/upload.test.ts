import { uploadReport, UploadError } from '@/lib/upload';

jest.mock('expo-image-manipulator', () => ({
  manipulateAsync: jest.fn(async () => ({ uri: 'file://out.webp' })),
  SaveFormat: { WEBP: 'webp' },
}));
jest.mock('@/api/patient', () => ({ signUpload: jest.fn(async () => ({ url: 'http://s/put', objectKey: 'reports/k1.webp' })) }));

const realFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = realFetch; });

test('returns the object key on success', async () => {
  globalThis.fetch = jest.fn(async () => ({ ok: true, blob: async () => new Blob(['x']) })) as unknown as typeof fetch;
  // second fetch (the PUT) also ok
  expect(await uploadReport('file://in.jpg')).toBe('reports/k1.webp');
});

test('throws storage UploadError when the PUT fails', async () => {
  let n = 0;
  globalThis.fetch = jest.fn(async () => {
    n += 1;
    if (n === 1) return { ok: true, blob: async () => new Blob(['x']) } as unknown as Response;
    return { ok: false, status: 503 } as unknown as Response;
  }) as unknown as typeof fetch;
  await expect(uploadReport('file://in.jpg')).rejects.toMatchObject({ kind: 'storage' });
});

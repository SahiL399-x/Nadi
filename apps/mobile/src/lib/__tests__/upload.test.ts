import { uploadReport, UploadError } from '@/lib/upload';

jest.mock('expo-image-manipulator', () => ({
  manipulateAsync: jest.fn(async () => ({ uri: 'file://out.webp' })),
  SaveFormat: { WEBP: 'webp' },
}));
jest.mock('@/api/patient', () => ({ signUpload: jest.fn(async () => ({ url: 'http://s/put', objectKey: 'reports/k1.webp' })) }));
import { signUpload } from '@/api/patient';

const realFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = realFetch; });

test('returns the object key on success', async () => {
  globalThis.fetch = jest.fn(async () => ({ ok: true, blob: async () => new Blob(['x']) })) as unknown as typeof fetch;
  // second fetch (the PUT) also ok
  expect(await uploadReport('file://in.jpg', { kind: 'image', source: 'upload' })).toBe('reports/k1.webp');
});

test('throws storage UploadError when the PUT fails', async () => {
  let n = 0;
  globalThis.fetch = jest.fn(async () => {
    n += 1;
    if (n === 1) return { ok: true, blob: async () => new Blob(['x']) } as unknown as Response;
    return { ok: false, status: 503 } as unknown as Response;
  }) as unknown as typeof fetch;
  await expect(uploadReport('file://in.jpg', { kind: 'image', source: 'upload' })).rejects.toMatchObject({ kind: 'storage' });
});

test('pdf uploads verbatim with application/pdf and upload source', async () => {
  (signUpload as jest.Mock).mockResolvedValue({ url: 'http://minio/k.pdf', objectKey: 'reports/upload/u/k.pdf' });
  globalThis.fetch = jest.fn(async (url: string, init?: any) => {
    if (typeof url === 'string' && url.startsWith('http://minio')) return { ok: true, status: 200 } as any;
    return { blob: async () => new Blob(['x']) } as any;
  }) as unknown as typeof fetch;
  const key = await uploadReport('file:///report.pdf', { kind: 'pdf', source: 'upload' });
  expect(signUpload).toHaveBeenCalledWith({ source: 'upload', ext: 'pdf' });
  const putCall = (fetch as jest.Mock).mock.calls.find((c) => c[0] === 'http://minio/k.pdf');
  expect(putCall[1].headers['content-type']).toBe('application/pdf');
  expect(key).toBe('reports/upload/u/k.pdf');
});

test('scanned image is webp with scan source', async () => {
  (signUpload as jest.Mock).mockResolvedValue({ url: 'http://minio/k.webp', objectKey: 'reports/scan/u/k.webp' });
  globalThis.fetch = jest.fn(async (url: string, init?: any) => {
    if (typeof url === 'string' && url.startsWith('http://minio')) return { ok: true, status: 200 } as any;
    return { blob: async () => new Blob(['x']) } as any;
  }) as unknown as typeof fetch;
  const key = await uploadReport('file:///page1.jpg', { kind: 'image', source: 'scan' });
  expect(signUpload).toHaveBeenCalledWith({ source: 'scan', ext: 'webp' });
  const putCall = (fetch as jest.Mock).mock.calls.find((c) => c[0] === 'http://minio/k.webp');
  expect(putCall[1].headers['content-type']).toBe('image/webp');
  expect(key).toBe('reports/scan/u/k.webp');
});

import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { z } from 'zod';
import { api, ApiError } from '@/api/client';
import { useSession } from '@/store/session';

const BASE = 'http://test.local';
process.env.EXPO_PUBLIC_API_URL = BASE;
const server = setupServer();
beforeAll(() => server.listen());
afterEach(() => { server.resetHandlers(); useSession.setState({ accessToken: null, refreshToken: 'r0' }); });
afterAll(() => server.close());

test('get parses a valid response', async () => {
  server.use(http.get(`${BASE}/v1/ping`, () => HttpResponse.json({ ok: true })));
  const out = await api.get('/v1/ping', z.object({ ok: z.boolean() }));
  expect(out.ok).toBe(true);
});

test('refreshes once on 401 then retries', async () => {
  let calls = 0;
  server.use(
    http.get(`${BASE}/v1/secure`, () => {
      calls += 1;
      return calls === 1 ? new HttpResponse(null, { status: 401 }) : HttpResponse.json({ ok: true });
    }),
    http.post(`${BASE}/v1/auth/refresh`, () => HttpResponse.json({ accessToken: 'new' })),
  );
  const out = await api.get('/v1/secure', z.object({ ok: z.boolean() }));
  expect(out.ok).toBe(true);
  expect(useSession.getState().accessToken).toBe('new');
});

test('signs out when refresh fails', async () => {
  server.use(
    http.get(`${BASE}/v1/secure`, () => new HttpResponse(null, { status: 401 })),
    http.post(`${BASE}/v1/auth/refresh`, () => new HttpResponse(null, { status: 401 })),
  );
  await expect(api.get('/v1/secure', z.object({ ok: z.boolean() }))).rejects.toBeInstanceOf(ApiError);
  expect(useSession.getState().accessToken).toBeNull();
});

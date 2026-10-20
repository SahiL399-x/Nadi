import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { bootstrapSession } from '@/api/bootstrap';
import { useSession } from '@/store/session';

const BASE = 'http://test.local';
process.env.EXPO_PUBLIC_API_URL = BASE;
const server = setupServer();
beforeAll(() => server.listen());
afterEach(() => { server.resetHandlers(); useSession.setState({ accessToken: null, refreshToken: null, role: null }); });
afterAll(() => server.close());

test('returns false with no stored refresh token', async () => {
  expect(await bootstrapSession()).toBe(false);
});

test('restores role from refresh', async () => {
  useSession.setState({ refreshToken: 'r1' });
  server.use(http.post(`${BASE}/v1/auth/refresh`, () =>
    HttpResponse.json({ accessToken: 'a', role: 'doctor', userId: 'u1' })));
  expect(await bootstrapSession()).toBe(true);
  expect(useSession.getState().role).toBe('doctor');
});

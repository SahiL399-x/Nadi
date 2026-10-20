import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { requestOtp, verifyOtp } from '@/api/auth';

const BASE = 'http://test.local';
process.env.EXPO_PUBLIC_API_URL = BASE;
const server = setupServer();
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

test('verifyOtp returns a parsed token pair with role', async () => {
  server.use(
    http.post(`${BASE}/v1/auth/request-otp`, () => HttpResponse.json({ sent: true })),
    http.post(`${BASE}/v1/auth/verify-otp`, () =>
      HttpResponse.json({ accessToken: 'a', refreshToken: 'r', role: 'pharmacy', userId: 'u9' })),
  );
  await requestOtp('+915000020001');
  const pair = await verifyOtp({ phone: '+915000020001', code: '123456' });
  expect(pair.role).toBe('pharmacy');
});

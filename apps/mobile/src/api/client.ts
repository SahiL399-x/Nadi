import { z } from 'zod';
import { useSession } from '@/store/session';

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

const baseUrl = (): string => {
  const url = process.env.EXPO_PUBLIC_API_URL;
  if (!url) throw new ApiError(0, 'EXPO_PUBLIC_API_URL is not set');
  return url;
};

async function refreshAccessToken(): Promise<boolean> {
  const { refreshToken, setAccessToken } = useSession.getState();
  if (!refreshToken) return false;
  const res = await fetch(`${baseUrl()}/v1/auth/refresh`, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ refreshToken }),
  });
  if (!res.ok) return false;
  const data = (await res.json()) as { accessToken?: string };
  if (!data.accessToken) return false;
  setAccessToken(data.accessToken);
  return true;
}

async function request(path: string, init: RequestInit, retry = true): Promise<Response> {
  const { accessToken } = useSession.getState();
  const headers: Record<string, string> = { ...(init.headers as Record<string, string>) };
  if (accessToken) headers.authorization = `Bearer ${accessToken}`;
  const res = await fetch(`${baseUrl()}${path}`, { ...init, headers });
  if (res.status === 401 && retry) {
    const ok = await refreshAccessToken();
    if (ok) return request(path, init, false);
    await useSession.getState().signOut();
    throw new ApiError(401, 'session expired');
  }
  if (!res.ok) throw new ApiError(res.status, `request failed: ${res.status}`);
  return res;
}

export const api = {
  async get<T>(path: string, schema: z.ZodType<T>): Promise<T> {
    const res = await request(path, { method: 'GET' });
    return schema.parse(await res.json());
  },
  async post<T>(path: string, body: unknown, schema?: z.ZodType<T>): Promise<T> {
    const res = await request(path, {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return schema ? schema.parse(data) : (data as T);
  },
  async put<T>(path: string, body: unknown, schema?: z.ZodType<T>): Promise<T> {
    const res = await request(path, {
      method: 'PUT', headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return schema ? schema.parse(data) : (data as T);
  },
};

export async function apiPutBytes(url: string, bytes: Blob, contentType: string): Promise<void> {
  const res = await fetch(url, { method: 'PUT', headers: { 'content-type': contentType }, body: bytes });
  if (!res.ok) throw new ApiError(res.status, 'upload failed');
}

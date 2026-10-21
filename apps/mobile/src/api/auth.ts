import { api } from '@/api/client';
import { TokenPairSchema, type TokenPair } from '@/api/schemas';
import { z } from 'zod';

export async function requestOtp(phone: string): Promise<void> {
  await api.post('/v1/auth/request-otp', { phone }, z.object({ sent: z.boolean() }));
}

export async function verifyOtp(input: {
  phone: string; code: string; name?: string; role?: string;
}): Promise<TokenPair> {
  return api.post('/v1/auth/verify-otp', {
    phone: input.phone, code: input.code, name: input.name ?? '', role: input.role ?? 'patient',
  }, TokenPairSchema);
}

import { z } from 'zod';
import { useSession } from '@/store/session';
import type { Role } from '@/theme/tokens';

const RefreshSchema = z.object({
  accessToken: z.string(), role: z.enum(['patient', 'doctor', 'pharmacy']), userId: z.string(),
});

export async function bootstrapSession(): Promise<boolean> {
  const { refreshToken, applyRefresh, signOut } = useSession.getState();
  if (!refreshToken) return false;
  const url = process.env.EXPO_PUBLIC_API_URL;
  try {
    const res = await fetch(`${url}/v1/auth/refresh`, {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ refreshToken }),
    });
    if (!res.ok) { await signOut(); return false; }
    const data = RefreshSchema.parse(await res.json());
    applyRefresh({ accessToken: data.accessToken, role: data.role as Role, userId: data.userId });
    return true;
  } catch { await signOut(); return false; }
}

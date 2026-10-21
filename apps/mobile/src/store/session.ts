import * as SecureStore from 'expo-secure-store';
import { create } from 'zustand';
import type { Role } from '@/theme/tokens';
import type { TokenPair } from '@/api/schemas';

const REFRESH_KEY = 'nadi.refresh';

type SessionState = {
  accessToken: string | null;
  refreshToken: string | null;
  role: Role | null;
  userId: string | null;
  signIn: (pair: TokenPair) => Promise<void>;
  setAccessToken: (token: string) => void;
  signOut: () => Promise<void>;
  restoreSession: () => Promise<void>;
  applyRefresh: (p: { accessToken: string; role: Role; userId: string }) => void;
};

export const useSession = create<SessionState>((set) => ({
  accessToken: null, refreshToken: null, role: null, userId: null,
  signIn: async (pair) => {
    await SecureStore.setItemAsync(REFRESH_KEY, pair.refreshToken);
    set({ accessToken: pair.accessToken, refreshToken: pair.refreshToken,
          role: pair.role, userId: pair.userId });
  },
  setAccessToken: (token) => set({ accessToken: token }),
  signOut: async () => {
    await SecureStore.deleteItemAsync(REFRESH_KEY);
    set({ accessToken: null, refreshToken: null, role: null, userId: null });
  },
  restoreSession: async () => {
    const token = await SecureStore.getItemAsync(REFRESH_KEY);
    if (token) set({ refreshToken: token });
  },
  applyRefresh: (p) => set({ accessToken: p.accessToken, role: p.role, userId: p.userId }),
}));

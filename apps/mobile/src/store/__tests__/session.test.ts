import * as SecureStore from 'expo-secure-store';
import { useSession } from '@/store/session';

const pair = { accessToken: 'a', refreshToken: 'r', role: 'doctor' as const, userId: 'u1' };

beforeEach(() => useSession.getState().signOut());

test('signIn stores tokens and persists refresh token', async () => {
  await useSession.getState().signIn(pair);
  expect(useSession.getState().accessToken).toBe('a');
  expect(useSession.getState().role).toBe('doctor');
  expect(SecureStore.setItemAsync).toHaveBeenCalledWith('nadi.refresh', 'r');
});

test('signOut clears state and secure storage', async () => {
  await useSession.getState().signIn(pair);
  await useSession.getState().signOut();
  expect(useSession.getState().accessToken).toBeNull();
  expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('nadi.refresh');
});

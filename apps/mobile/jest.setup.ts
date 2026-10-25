// @testing-library/react-native v14 bundles jest-native matchers into the
// main entrypoint and auto-extends `expect` on import; the standalone
// `extend-expect` subpath from older versions no longer exists.
import '@testing-library/react-native';

jest.mock('expo-secure-store', () => {
  const store: Record<string, string> = {};
  return {
    setItemAsync: jest.fn(async (k: string, v: string) => { store[k] = v; }),
    getItemAsync: jest.fn(async (k: string) => store[k] ?? null),
    deleteItemAsync: jest.fn(async (k: string) => { delete store[k]; }),
  };
}, { virtual: true });

// Under jest-expo the native notification scheduler never settles, so the
// fire-and-forget `notify()` call (now wired into hooks across all three
// portals) leaves `act()` hanging. Stub the OS calls so they resolve
// immediately; `notify()`'s in-app feed logic still runs for real.
jest.mock('expo-notifications', () => ({
  scheduleNotificationAsync: jest.fn(async () => 'stub-id'),
  requestPermissionsAsync: jest.fn(async () => ({ status: 'granted', granted: true })),
}), { virtual: true });

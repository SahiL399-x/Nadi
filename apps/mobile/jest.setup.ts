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

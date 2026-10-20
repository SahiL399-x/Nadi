// expo's native fetch (backed by a native module) can't be lazily resolved inside Jest's
// RN test environment; fall back to React Native's own fetch polyfill for tests that need
// a real network-interceptable `fetch` (e.g. msw-based API client tests).
process.env.EXPO_PUBLIC_USE_RN_FETCH = '1';

module.exports = {
  preset: 'jest-expo',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@nadi/shared-types$': '<rootDir>/../../packages/shared-types/src/types.ts',
  },
  transformIgnorePatterns: [
    'node_modules/(?!((jest-)?react-native|@react-native(-community)?|expo(nent)?|@expo(nent)?/.*|@expo-google-fonts/.*|react-navigation|@react-navigation/.*|@unimodules/.*|unimodules|sentry-expo|native-base|react-native-svg|nativewind|react-native-css-interop|msw|@mswjs/.*|@msw/.*|@open-draft/.*|headers-polyfill|outvariant|until-async|is-node-process|rettime|cookie|strict-event-emitter))',
  ],
  transform: { '^.+\\.(js|jsx|ts|tsx|mjs)$': 'babel-jest' },
  testEnvironmentOptions: {
    customExportConditions: [''],
  },
};

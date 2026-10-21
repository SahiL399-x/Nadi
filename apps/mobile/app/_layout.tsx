import '../global.css';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { Stack } from 'expo-router';
import { QueryProvider } from '@/providers/QueryProvider';
import { ConnectivityBanner } from '@/components/ConnectivityBanner';

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <QueryProvider>
        <ConnectivityBanner />
        <Stack screenOptions={{ headerShown: false }} />
      </QueryProvider>
    </GestureHandlerRootView>
  );
}

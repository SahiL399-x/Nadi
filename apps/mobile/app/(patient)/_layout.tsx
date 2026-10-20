import { Stack } from 'expo-router';
import { ThemeProvider } from '@/providers/ThemeProvider';
export default function PatientLayout() {
  return (
    <ThemeProvider role="patient">
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="(tabs)" />
      </Stack>
    </ThemeProvider>
  );
}

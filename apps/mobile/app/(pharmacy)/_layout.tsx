import { Stack } from 'expo-router';
import { ThemeProvider } from '@/providers/ThemeProvider';
export default function PharmacyLayout() {
  return <ThemeProvider role="pharmacy"><Stack screenOptions={{ headerShown: false }} /></ThemeProvider>;
}

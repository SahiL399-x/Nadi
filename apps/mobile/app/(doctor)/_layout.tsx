import { Stack } from 'expo-router';
import { ThemeProvider } from '@/providers/ThemeProvider';
export default function DoctorLayout() {
  return <ThemeProvider role="doctor"><Stack screenOptions={{ headerShown: false }} /></ThemeProvider>;
}

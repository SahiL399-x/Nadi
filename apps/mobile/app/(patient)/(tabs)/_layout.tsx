import { Tabs } from 'expo-router';
import { useTheme } from '@/providers/ThemeProvider';
export default function PatientTabs() {
  const theme = useTheme();
  return (
    <Tabs screenOptions={{ headerShown: false, tabBarActiveTintColor: theme.primary }}>
      <Tabs.Screen name="index" options={{ title: 'Home' }} />
      <Tabs.Screen name="account" options={{ title: 'Account' }} />
    </Tabs>
  );
}

import { Tabs } from 'expo-router';
import { House, CalendarDays, FlaskConical, FileText, User } from 'lucide-react-native';
import { useTheme } from '@/providers/ThemeProvider';
import { colors } from '@/theme/tokens';

export default function PatientTabs() {
  const theme = useTheme();
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: theme.primary,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarStyle: { height: 64, paddingTop: 6, paddingBottom: 8, backgroundColor: colors.surface, borderTopColor: colors.border },
        tabBarLabelStyle: { fontSize: 11, fontWeight: '600' },
      }}
    >
      <Tabs.Screen name="index" options={{ title: 'Home', tabBarIcon: ({ color, size }) => <House color={color} size={size - 2} /> }} />
      <Tabs.Screen name="appointments" options={{ title: 'Visits', tabBarIcon: ({ color, size }) => <CalendarDays color={color} size={size - 2} /> }} />
      <Tabs.Screen name="records" options={{ title: 'Reports', tabBarIcon: ({ color, size }) => <FlaskConical color={color} size={size - 2} /> }} />
      <Tabs.Screen name="prescriptions" options={{ title: 'Rx', tabBarIcon: ({ color, size }) => <FileText color={color} size={size - 2} /> }} />
      <Tabs.Screen name="account" options={{ title: 'Account', tabBarIcon: ({ color, size }) => <User color={color} size={size - 2} /> }} />
    </Tabs>
  );
}

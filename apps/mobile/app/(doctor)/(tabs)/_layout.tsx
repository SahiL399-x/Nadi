import { Tabs } from 'expo-router';
import { LayoutDashboard, ListChecks, CalendarDays, UserCog } from 'lucide-react-native';
import { useTheme } from '@/providers/ThemeProvider';
import { colors } from '@/theme/tokens';

export default function DoctorTabs() {
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
      <Tabs.Screen name="index" options={{ title: 'Home', tabBarIcon: ({ color, size }) => <LayoutDashboard color={color} size={size - 2} /> }} />
      <Tabs.Screen name="queue" options={{ title: 'Queue', tabBarIcon: ({ color, size }) => <ListChecks color={color} size={size - 2} /> }} />
      <Tabs.Screen name="appointments" options={{ title: 'Appts', tabBarIcon: ({ color, size }) => <CalendarDays color={color} size={size - 2} /> }} />
      <Tabs.Screen name="profile" options={{ title: 'Profile', tabBarIcon: ({ color, size }) => <UserCog color={color} size={size - 2} /> }} />
    </Tabs>
  );
}

import { Tabs } from 'expo-router';
import { LayoutDashboard, ClipboardList, Inbox } from 'lucide-react-native';
import { useTheme } from '@/providers/ThemeProvider';
import { colors } from '@/theme/tokens';

export default function PharmacyTabs() {
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
      <Tabs.Screen name="orders" options={{ title: 'Orders', tabBarIcon: ({ color, size }) => <ClipboardList color={color} size={size - 2} /> }} />
      <Tabs.Screen name="inbox" options={{ title: 'Requests', tabBarIcon: ({ color, size }) => <Inbox color={color} size={size - 2} /> }} />
    </Tabs>
  );
}

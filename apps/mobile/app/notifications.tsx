import { ScrollView, Text, View } from 'react-native';
import { Bell as BellIcon } from 'lucide-react-native';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { useNotifications } from '@/store/notifications';
import { colors, radii, shadow, spacing, type as t } from '@/theme/tokens';

export default function Notifications() {
  const items = useNotifications((s) => s.items);
  const clear = useNotifications((s) => s.clear);
  return (
    <View style={{ flex: 1, backgroundColor: colors.pageBg }}>
      <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.sm, paddingBottom: spacing.xxl }}>
        <Text style={{ fontSize: t.h2, fontWeight: '800', color: colors.text }}>Notifications</Text>
        {items.length === 0 ? (
          <EmptyState title="No notifications" message="Updates about appointments, prescriptions and orders appear here." />
        ) : (
          items.map((n) => (
            <View key={n.id} style={{ flexDirection: 'row', gap: spacing.sm, backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.md, ...shadow.card }}>
              <View style={{ width: 36, height: 36, borderRadius: 18, backgroundColor: colors.greenTint, alignItems: 'center', justifyContent: 'center' }}>
                <BellIcon size={18} color={colors.brightGreen} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={{ fontSize: t.sm, fontWeight: '800', color: colors.text }}>{n.title}</Text>
                <Text style={{ fontSize: t.sm, color: colors.textMuted }}>{n.body}</Text>
              </View>
            </View>
          ))
        )}
        {items.length > 0 ? <Button title="Clear all" variant="ghost" color={colors.textMuted} onPress={clear} /> : null}
      </ScrollView>
    </View>
  );
}

import { Text, View } from 'react-native';
import { colors, spacing, type as t } from '@/theme/tokens';
export function EmptyState({ title, message }: { title: string; message: string }) {
  return <View style={{ alignItems: 'center', padding: spacing.xl, gap: spacing.sm }}>
    <Text style={{ fontSize: t.h3, color: colors.text, fontWeight: '600' }}>{title}</Text>
    <Text style={{ fontSize: t.sm, color: colors.textMuted, textAlign: 'center' }}>{message}</Text>
  </View>;
}

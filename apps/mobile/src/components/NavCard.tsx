import type { ComponentType } from 'react';
import { Pressable, Text } from 'react-native';
import { colors, radii, spacing, type as t } from '@/theme/tokens';

type Props = { label: string; onPress: () => void; Icon: ComponentType<{ size?: number; color?: string }>; color?: string };
export function NavCard({ label, onPress, Icon, color }: Props) {
  return (
    <Pressable onPress={onPress} style={{ width: '47%', flexDirection: 'row', alignItems: 'center',
      gap: spacing.sm, backgroundColor: colors.surface, borderRadius: radii.md, borderWidth: 1,
      borderColor: colors.border, padding: spacing.md, minHeight: 56 }}>
      <Icon size={22} color={color ?? colors.navy} />
      <Text style={{ fontSize: t.sm, color: colors.text, fontWeight: '600', flex: 1 }}>{label}</Text>
    </Pressable>
  );
}

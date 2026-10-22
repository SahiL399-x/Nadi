import { Pressable, ScrollView, Text } from 'react-native';
import { colors, spacing, type as t } from '@/theme/tokens';

type Option = { label: string; value: string };
export function FilterChips({ options, value, onChange, color }:
  { options: Option[]; value: string; onChange: (v: string) => void; color?: string }) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false}
      contentContainerStyle={{ gap: spacing.sm, paddingHorizontal: spacing.lg }}>
      {options.map((o) => (
        <Pressable key={o.value} onPress={() => onChange(o.value)} style={{ paddingVertical: 8, paddingHorizontal: 16,
          borderRadius: 999, backgroundColor: value === o.value ? (color ?? colors.navy) : colors.lightGrey }}>
          <Text style={{ color: value === o.value ? colors.white : colors.text, fontSize: t.sm }}>{o.label}</Text>
        </Pressable>
      ))}
    </ScrollView>
  );
}

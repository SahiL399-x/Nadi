import { Pressable, Text, View } from 'react-native';
import { SPECIALTIES, type Specialty } from '@/features/patient/specialties';
import { colors, radii, shadow, spacing, type as t } from '@/theme/tokens';

// Color-coded (soft green) icon badges in a 3-up grid — Practo-style browse
// layout, kept on lucide icons rather than photos.
export function SpecialtyGrid({ onSelect }: { onSelect: (s: Specialty) => void }) {
  return (
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', rowGap: spacing.md }}>
      {SPECIALTIES.map((s) => (
        <Pressable
          key={s.label}
          onPress={() => onSelect(s)}
          style={{ width: '31%', alignItems: 'center', gap: spacing.sm, backgroundColor: colors.surface,
            borderRadius: radii.lg, paddingVertical: spacing.md, paddingHorizontal: spacing.xs, ...shadow.card }}
        >
          <View style={{ width: 54, height: 54, borderRadius: 27, backgroundColor: colors.greenTint,
            alignItems: 'center', justifyContent: 'center' }}>
            <s.Icon size={26} color={colors.brightGreen} />
          </View>
          <Text numberOfLines={2} style={{ fontSize: t.xs, color: colors.text, fontWeight: '600', textAlign: 'center' }}>
            {s.label}
          </Text>
        </Pressable>
      ))}
    </View>
  );
}

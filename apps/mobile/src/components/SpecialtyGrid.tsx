import { Pressable, Text, View } from 'react-native';
import { SPECIALTIES, type Specialty } from '@/features/patient/specialties';
import { colors, radii, spacing, type as t } from '@/theme/tokens';

export function SpecialtyGrid({ onSelect }: { onSelect: (s: Specialty) => void }) {
  return (
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm }}>
      {SPECIALTIES.map((s) => (
        <Pressable key={s.label} onPress={() => onSelect(s)}
          style={{ width: '47%', backgroundColor: colors.surface, borderRadius: radii.md,
            borderWidth: 1, borderColor: colors.border, padding: spacing.md, gap: spacing.sm }}>
          <s.Icon size={28} color={colors.seaGreen} />
          <Text style={{ fontSize: t.sm, color: colors.text, fontWeight: '600' }}>{s.label}</Text>
        </Pressable>
      ))}
    </View>
  );
}

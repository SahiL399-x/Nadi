import { Text, View } from 'react-native';
import type { TriageResult } from '@/api/schemas';
import { colors, radii, spacing, type as t } from '@/theme/tokens';

export function NadiNote({ triage }: { triage: TriageResult }) {
  const top = triage.specialties[0];
  return (
    <View style={{ backgroundColor: colors.lightBlue, borderRadius: radii.md, padding: spacing.md,
      borderWidth: 1, borderColor: colors.navy, gap: spacing.sm }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <Text style={{ fontSize: t.sm, color: colors.navy, fontWeight: '800' }}>NADI NOTE</Text>
      </View>
      <Text style={{ fontSize: t.body, color: colors.text }}>
        Suggested: {top?.name ?? '—'}
      </Text>
    </View>
  );
}

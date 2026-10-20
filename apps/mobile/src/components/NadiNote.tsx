import { Text, View } from 'react-native';
import { AcuityBadge } from '@/components/ui/AcuityBadge';
import type { TriageResult } from '@/api/schemas';
import { colors, radii, spacing, type as t } from '@/theme/tokens';

export function NadiNote({ triage }: { triage: TriageResult }) {
  const top = triage.specialties[0];
  return (
    <View style={{ backgroundColor: colors.lightBlue, borderRadius: radii.md, padding: spacing.md,
      borderWidth: 1, borderColor: colors.navy, gap: spacing.sm }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <Text style={{ fontSize: t.sm, color: colors.navy, fontWeight: '800' }}>NADI NOTE</Text>
        <AcuityBadge acuity={triage.acuity} />
      </View>
      <Text style={{ fontSize: t.body, color: colors.text }}>
        Suggested: {top?.name ?? '—'} · confidence {Math.round(triage.acuityConfidence * 100)}%
      </Text>
      <Text style={{ fontSize: t.xs, color: colors.navy }}>Drivers</Text>
      {triage.drivers.map((d, i) => (
        <Text key={i} style={{ fontSize: t.sm, color: colors.text }}>• {d.feature} ({Math.round(d.contribution * 100)}%)</Text>
      ))}
    </View>
  );
}

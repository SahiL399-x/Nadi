import { ScrollView, Text, View } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { Card } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import { ErrorState } from '@/components/ui/ErrorState';
import { usePatient } from '@/features/doctor/usePatient';
import { colors, spacing, type as t } from '@/theme/tokens';

function Section({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  return (
    <Card>
      <Text style={{ fontSize: t.sm, color: colors.textMuted, marginBottom: spacing.xs }}>{title}</Text>
      {items.length === 0 ? <Text style={{ fontSize: t.sm, color: colors.text }}>{empty}</Text>
        : items.map((it, i) => <Text key={i} style={{ fontSize: t.sm, color: colors.text }}>• {it}</Text>)}
    </Card>
  );
}

export default function PatientFile() {
  const { pid } = useLocalSearchParams<{ pid: string }>();
  const { data, isLoading, isError, refetch } = usePatient(pid!);
  if (isLoading) return <View style={{ padding: spacing.lg, gap: spacing.md }}><Skeleton height={28} /><Skeleton height={120} /></View>;
  if (isError || !data) return <ErrorState message="Could not load this patient." onRetry={refetch} />;
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.h2, fontWeight: '700', color: colors.text }}>{data.name}, {data.age}{data.sex}</Text>
      <Section title="Conditions" items={data.conditions} empty="None recorded" />
      <Section title="Allergies" items={data.allergies} empty={data.noKnownAllergies ? 'No known allergies' : 'None recorded'} />
      <Section title="Family history" items={data.familyHistory} empty="None recorded" />
      <Card>
        <Text style={{ fontSize: t.sm, color: colors.textMuted, marginBottom: spacing.xs }}>Latest visit</Text>
        {data.latestVisit ? (
          <Text style={{ fontSize: t.sm, color: colors.text }}>
            {data.latestVisit.visitedAt} — {data.latestVisit.summary} ({data.latestVisit.status})
          </Text>
        ) : <Text style={{ fontSize: t.sm, color: colors.text }}>No visits yet</Text>}
      </Card>
      <Section title="Past prescriptions" items={data.prescriptions} empty="None issued" />
    </ScrollView>
  );
}

import { ScrollView, Text, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { NadiNote } from '@/components/NadiNote';
import { useQueue } from '@/features/doctor/useQueue';
import type { QueueItem } from '@/api/schemas';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function DoctorCase() {
  const { cid } = useLocalSearchParams<{ cid: string }>();
  const qc = useQueryClient();
  const { data } = useQueue();
  const item = (qc.getQueryData<QueueItem>(['queueItem', cid])
    ?? data?.find((q) => q.id === cid)) as QueueItem | undefined;
  if (!item) return <View style={{ padding: spacing.lg }}><Text style={{ color: colors.textMuted }}>Loading case…</Text></View>;
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.h2, fontWeight: '700', color: colors.text }}>
        {item.patientName}, {item.patientAge}{item.patientSex}
      </Text>
      <Text style={{ fontSize: t.sm, color: colors.textMuted }}>Complaint: {item.complaint}</Text>
      <NadiNote triage={item.triage} />
      {item.triage.labs.length > 0 ? (
        <Card>
          <Text style={{ fontSize: t.sm, color: colors.textMuted }}>Labs</Text>
          {item.triage.labs.map((l, i) => (
            <Text key={i} style={{ fontSize: t.sm, color: l.flag === 'N' ? colors.text : colors.urgent }}>
              {l.analyte}: {l.value} {l.unit} [{l.refRange}] ({l.flag})
            </Text>
          ))}
        </Card>
      ) : null}
      <Button title="Start consultation" color={colors.navy}
        onPress={() => router.push({ pathname: '/(doctor)/room/[cid]', params: { cid: item.id } })} />
      <Button title="Write prescription" color={colors.navy}
        onPress={() => router.push({ pathname: '/(doctor)/prescribe/[cid]', params: { cid: item.id } })} />
      <Button title="Refer to another specialty" variant="ghost" color={colors.navy}
        onPress={() => router.push({ pathname: '/(doctor)/refer/[cid]', params: { cid: item.id } })} />
    </ScrollView>
  );
}

import { useState } from 'react';
import { ScrollView, Text, View } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import { Button, Card, Skeleton } from '@/components/ui';
import { usePrescription } from '@/features/patient/usePrescription';
import { useConsent } from '@/features/patient/useConsent';
import { listPharmacies } from '@/api/patient';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function PrescriptionScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { prescriptionId, prescription, waiting } = usePrescription(id!);
  const pharmacies = useQuery({ queryKey: ['pharmacies'], queryFn: listPharmacies });
  const { submit, pending, done } = useConsent();
  const [picked, setPicked] = useState<string[]>([]);
  const toggle = (pid: string) => setPicked((xs) => xs.includes(pid) ? xs.filter((x) => x !== pid) : [...xs, pid]);

  if (waiting || !prescription) return (
    <View style={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.body, color: colors.textMuted }}>Waiting for your doctor's prescription…</Text>
      <Skeleton height={120} />
    </View>
  );
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.h2, fontWeight: '700', color: colors.text }}>Prescription</Text>
      <Card>{prescription.lines.map((l, i) => (
        <Text key={i} style={{ color: colors.text, fontSize: t.sm }}>{l.drug} {l.strength} — {l.frequency}, {l.durationDays}d</Text>
      ))}</Card>
      <Text style={{ fontSize: t.body, fontWeight: '600', color: colors.text }}>Choose your pharmacy</Text>
      <Text style={{ fontSize: t.xs, color: colors.textMuted }}>Required — you choose who receives it. Nothing is pre-selected.</Text>
      {(pharmacies.data ?? []).map((p) => (
        <Button key={p.id} title={`${picked.includes(p.id) ? '✓ ' : ''}${p.name} · ${p.distanceKm}km${p.isOpen ? '' : ' (closed)'}`}
          variant={picked.includes(p.id) ? 'primary' : 'ghost'} color={colors.navy} onPress={() => toggle(p.id)} />
      ))}
      <Button title="Send to selected pharmacies" disabled={picked.length === 0 || done} loading={pending}
        onPress={() => prescriptionId && submit(prescriptionId, picked)} />
      {done ? <Text style={{ color: colors.routine, fontSize: t.body }}>Status: {prescription.status}</Text> : null}
    </ScrollView>
  );
}

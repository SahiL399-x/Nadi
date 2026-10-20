import { useState } from 'react';
import { Pressable, ScrollView, Text } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { usePrescribe } from '@/features/doctor/usePrescribe';
import type { PrescriptionLineInput } from '@/api/doctor';
import { colors, spacing, type as t } from '@/theme/tokens';

const blank = (): PrescriptionLineInput => ({ drug: '', strength: '', frequency: '', durationDays: 3 });

export default function Prescribe() {
  const { cid } = useLocalSearchParams<{ cid: string }>();
  const { submit, pending } = usePrescribe();
  const [lines, setLines] = useState<PrescriptionLineInput[]>([blank()]);
  const patch = (i: number, p: Partial<PrescriptionLineInput>) =>
    setLines((xs) => xs.map((x, j) => (j === i ? { ...x, ...p } : x)));
  const valid = lines.every((l) => l.drug.trim() && l.strength.trim() && l.frequency.trim());
  const save = async () => { await submit(cid!, lines); router.replace('/(doctor)'); };
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.h2, fontWeight: '700', color: colors.text }}>New prescription</Text>
      {lines.map((l, i) => (
        <Card key={i}>
          <Input value={l.drug} onChangeText={(v) => patch(i, { drug: v })} placeholder="Drug" />
          <Input value={l.strength} onChangeText={(v) => patch(i, { strength: v })} placeholder="Strength (e.g. 500mg)" />
          <Input value={l.frequency} onChangeText={(v) => patch(i, { frequency: v })} placeholder="Frequency (e.g. BD)" />
          <Input value={String(l.durationDays)} onChangeText={(v) => patch(i, { durationDays: Number(v) || 0 })} keyboardType="number-pad" placeholder="Days" />
          {lines.length > 1 ? <Pressable onPress={() => setLines((xs) => xs.filter((_, j) => j !== i))}>
            <Text style={{ color: colors.emergency }}>Remove</Text></Pressable> : null}
        </Card>
      ))}
      <Button title="+ Add medicine" variant="ghost" color={colors.navy} onPress={() => setLines((xs) => [...xs, blank()])} />
      <Button title="Issue prescription" color={colors.navy} loading={pending} disabled={!valid} onPress={save} />
    </ScrollView>
  );
}

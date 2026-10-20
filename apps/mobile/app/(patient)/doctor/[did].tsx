import { useState } from 'react';
import { ScrollView, Text, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Avatar, Button, Card, Skeleton } from '@/components/ui';
import { useDoctor } from '@/features/patient/useDoctor';
import { useBook } from '@/features/patient/useBook';
import { ensureConsultation } from '@/api/patient';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function DoctorDetail() {
  const { did, id } = useLocalSearchParams<{ did: string; id?: string }>();
  const { data: d, isLoading } = useDoctor(did!);
  const { confirm, pending } = useBook();
  const [slot, setSlot] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  if (isLoading || !d) return <View style={{ padding: spacing.lg }}><Skeleton height={200} /></View>;
  const bookNow = async () => {
    if (!slot) return;
    setBusy(true);
    try {
      const cid = await ensureConsultation(id, d.specialty); // existing id on triage path; created on direct browse
      const ok = await confirm(cid, d.id, slot);
      if (ok) router.replace({ pathname: '/(patient)/booked', params: { id: cid, slot, name: d.name } });
    } finally { setBusy(false); }
  };
  return (
    <View style={{ flex: 1 }}>
      <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
        <View style={{ alignItems: 'center', gap: spacing.sm }}>
          <Avatar uri={d.photoUrl} size={96} />
          <Text style={{ fontSize: t.h2, fontWeight: '700', color: colors.text }}>{d.name}</Text>
          <Text style={{ fontSize: t.sm, color: colors.textMuted }}>{d.specialty} · {d.experienceYears} yrs</Text>
        </View>
        <Card><Text style={{ color: colors.text }}>Languages: {d.languages.join(', ')}  ·  Fee ₹{d.feeInr}</Text></Card>
        <Text style={{ fontSize: t.body, fontWeight: '600', color: colors.text }}>Pick a time slot</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm }}>
          {d.availableSlots.map((s) => (
            <Button key={s} title={s} variant={slot === s ? 'primary' : 'ghost'} color={colors.navy}
              onPress={() => setSlot(s)} />
          ))}
        </View>
      </ScrollView>
      <View style={{ padding: spacing.lg, borderTopWidth: 1, borderColor: colors.border }}>
        <Button title={slot ? `Book ${slot}` : 'Select a slot'} onPress={bookNow} loading={busy || pending} disabled={!slot || busy} />
      </View>
    </View>
  );
}

import { useEffect } from 'react';
import { ScrollView, Text, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { useOfferActions } from '@/features/pharmacy/useOfferActions';
import type { Offer } from '@/api/schemas';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function Order() {
  const { oid } = useLocalSearchParams<{ oid: string }>();
  const qc = useQueryClient();
  const offer = qc.getQueryData<Offer>(['offer', oid]);
  const { accept, decline, pending, result } = useOfferActions();
  useEffect(() => {
    if (!result) return;
    const id = setTimeout(() => { void qc.invalidateQueries({ queryKey: ['inbox'] }); router.replace('/(pharmacy)'); }, 1400);
    return () => clearTimeout(id);
  }, [result, qc]);
  if (!offer) return <View style={{ padding: spacing.lg }}><Text style={{ color: colors.textMuted }}>Order not found.</Text></View>;
  if (result) return (
    <View style={{ flex: 1, justifyContent: 'center', padding: spacing.xl }}>
      <Text style={{ fontSize: t.h2, color: colors.navy, fontWeight: '700' }}>
        {result === 'accepted' ? 'Order accepted' : result === 'forwarded' ? 'Declined — forwarded to the next pharmacy' : 'Order declined'}
      </Text>
    </View>
  );
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.h2, fontWeight: '700', color: colors.text }}>Order for {offer.patientName}</Text>
      <Card>{offer.lines.map((l, i) => (
        <Text key={i} style={{ color: colors.text, fontSize: t.sm }}>{l.drug} {l.strength} — {l.frequency}, {l.durationDays}d</Text>
      ))}</Card>
      <Button title="Accept order" color={colors.navy} loading={pending} onPress={() => accept(oid!)} />
      <Button title="Decline" variant="ghost" color={colors.emergency} disabled={pending} onPress={() => decline(oid!)} />
    </ScrollView>
  );
}

import { useState } from 'react';
import { ScrollView, Text, View } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { useOrderTransition } from '@/features/pharmacy/useOrderTransition';
import { nextStatuses, STATUS_LABEL, type Order } from '@/api/pharmacyPortal';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function OrderDetail() {
  const { oid } = useLocalSearchParams<{ oid: string }>();
  const qc = useQueryClient();
  const cached = qc.getQueryData<Order>(['orderDetail', oid]);
  const [status, setStatus] = useState<string>(cached?.status ?? '');
  const { advance, pending, error } = useOrderTransition();
  if (!cached) {
    return (
      <View style={{ padding: spacing.lg }}>
        <Text style={{ color: colors.textMuted }}>Order not found.</Text>
      </View>
    );
  }
  const options = nextStatuses(status);
  const go = async (next: string) => {
    const ok = await advance(oid!, next);
    if (ok) setStatus(ok);
  };
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.h2, fontWeight: '800', color: colors.orange }}>{cached.orderNo}</Text>
      <Card>
        <Text style={{ fontSize: t.body, fontWeight: '700', color: colors.text }}>{cached.patientName}</Text>
        <Text style={{ fontSize: t.sm, color: colors.textMuted }}>{cached.phone}</Text>
        <Text style={{ fontSize: t.sm, color: colors.text }}>{cached.itemsCount} item(s) · ₹{cached.totalInr}</Text>
        <Text style={{ fontSize: t.sm, color: colors.orange, fontWeight: '700', marginTop: spacing.xs }}>
          Status: {STATUS_LABEL[status] ?? status}
        </Text>
      </Card>
      {error ? <Text style={{ color: colors.emergency, fontSize: t.sm }}>{error}</Text> : null}
      {options.length === 0 ? (
        <Text style={{ fontSize: t.sm, color: colors.textMuted }}>This order is complete — no further action.</Text>
      ) : (
        options.map((next) => (
          <Button
            key={next}
            title={`Mark ${STATUS_LABEL[next] ?? next}`}
            loading={pending}
            color={next === 'CANCELLED' ? colors.emergency : colors.orange}
            variant={next === 'CANCELLED' ? 'ghost' : 'primary'}
            onPress={() => go(next)}
          />
        ))
      )}
    </ScrollView>
  );
}

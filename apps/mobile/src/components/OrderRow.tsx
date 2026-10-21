import { Pressable, Text, View } from 'react-native';
import { Card } from '@/components/ui/Card';
import type { Order } from '@/api/pharmacyPortal';
import { STATUS_LABEL } from '@/api/pharmacyPortal';
import { colors, spacing, type as t } from '@/theme/tokens';

export function OrderRow({ order, onPress }: { order: Order; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} style={{ marginBottom: spacing.sm }}>
      <Card>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
          <Text style={{ fontSize: t.body, fontWeight: '800', color: colors.navy }}>{order.orderNo}</Text>
          <Text style={{ fontSize: t.xs, color: colors.navy, fontWeight: '700' }}>
            {STATUS_LABEL[order.status] ?? order.status}
          </Text>
        </View>
        <Text style={{ fontSize: t.sm, color: colors.text }}>{order.patientName}</Text>
        <Text style={{ fontSize: t.sm, color: colors.textMuted }}>
          {order.itemsCount} item(s) · ₹{order.totalInr}
        </Text>
      </Card>
    </Pressable>
  );
}

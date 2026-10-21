import { useState } from 'react';
import { View } from 'react-native';
import { FlashList } from '@shopify/flash-list';
import { router } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Skeleton } from '@/components/ui/Skeleton';
import { FilterChips } from '@/components/FilterChips';
import { OrderRow } from '@/components/OrderRow';
import { useOrders } from '@/features/pharmacy/useOrders';
import type { OrderStatusFilter } from '@/api/pharmacyPortal';
import { spacing } from '@/theme/tokens';

const OPTS = [
  { label: 'All', value: 'all' }, { label: 'New', value: 'pending' },
  { label: 'Preparing', value: 'preparing' }, { label: 'Out for delivery', value: 'out_for_delivery' },
  { label: 'Delivered', value: 'delivered' }, { label: 'Completed', value: 'completed' },
];

export default function Orders() {
  const [status, setStatus] = useState<OrderStatusFilter>('all');
  const { data, isLoading, isError, refetch } = useOrders(status);
  const qc = useQueryClient();
  return (
    <View style={{ flex: 1, paddingTop: spacing.lg, gap: spacing.sm }}>
      <FilterChips options={OPTS} value={status} onChange={(v) => setStatus(v as OrderStatusFilter)} />
      {isLoading ? (
        <View style={{ padding: spacing.lg, gap: spacing.sm }}>{[0, 1, 2].map((i) => <Skeleton key={i} height={84} />)}</View>
      ) : isError ? <ErrorState message="Could not load orders." onRetry={refetch} /> : (
        <FlashList data={data ?? []} keyExtractor={(o) => o.id}
          contentContainerStyle={{ padding: spacing.lg }}
          ListEmptyComponent={<EmptyState title="No orders" message="Orders in this state will appear here." />}
          renderItem={({ item }) => (
            <OrderRow order={item} onPress={() => {
              qc.setQueryData(['orderDetail', item.id], item);
              router.push({ pathname: '/(pharmacy)/orders/[oid]', params: { oid: item.id } });
            }} />
          )} />
      )}
    </View>
  );
}

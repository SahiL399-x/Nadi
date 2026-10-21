import { Text, View, Pressable } from 'react-native';
import { FlashList } from '@shopify/flash-list';
import { router } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';
import { Card } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Skeleton } from '@/components/ui/Skeleton';
import { useInbox } from '@/features/pharmacy/useInbox';
import type { Offer } from '@/api/schemas';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function PharmacyInboxScreen() {
  const { data, isLoading, isError, refetch } = useInbox();
  const qc = useQueryClient();
  if (isLoading) return <View style={{ padding: spacing.lg, gap: spacing.sm }}>{[0, 1].map((i) => <Skeleton key={i} height={88} />)}</View>;
  if (isError) return <ErrorState message="Could not load the inbox." onRetry={refetch} />;
  return (
    <FlashList data={data ?? []} keyExtractor={(o) => o.id}
      contentContainerStyle={{ padding: spacing.lg }}
      ListEmptyComponent={<EmptyState title="No new orders" message="Incoming prescriptions will appear here." />}
      renderItem={({ item }: { item: Offer }) => (
        <View style={{ marginBottom: spacing.sm }}>
          <Card>
            <Text style={{ fontSize: t.body, fontWeight: '700', color: colors.text }}>{item.patientName}</Text>
            <Text style={{ fontSize: t.sm, color: colors.textMuted }}>{item.lines.length} item(s)</Text>
            <Pressable onPress={() => { qc.setQueryData(['offer', item.id], item);
              router.push({ pathname: '/(pharmacy)/order/[oid]', params: { oid: item.id } }); }}
              style={{ minHeight: 48, justifyContent: 'center', marginTop: spacing.xs }}>
              <Text style={{ color: colors.navy, fontSize: t.sm }}>View order →</Text>
            </Pressable>
          </Card>
        </View>
      )} />
  );
}

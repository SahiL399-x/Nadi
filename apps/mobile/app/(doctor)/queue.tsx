import { View } from 'react-native';
import { FlashList } from '@shopify/flash-list';
import { router } from 'expo-router';
import { QueueRow } from '@/components/QueueRow';
import { EmptyState, ErrorState, Skeleton } from '@/components/ui';
import { useQueue } from '@/features/doctor/useQueue';
import { useQueryClient } from '@tanstack/react-query';
import { spacing } from '@/theme/tokens';

export default function DoctorQueueScreen() {
  const { data, isLoading, isError, refetch } = useQueue();
  const qc = useQueryClient();
  if (isLoading) return <View style={{ padding: spacing.lg, gap: spacing.sm }}>{[0, 1, 2].map((i) => <Skeleton key={i} height={88} />)}</View>;
  if (isError) return <ErrorState message="Could not load the queue." onRetry={refetch} />;
  return (
    <FlashList data={data ?? []} keyExtractor={(i) => i.id}
      contentContainerStyle={{ padding: spacing.lg }}
      ListEmptyComponent={<EmptyState title="No patients in your queue" message="Booked patients will appear here." />}
      renderItem={({ item }) => <QueueRow item={item} onPress={() => {
        qc.setQueryData(['queueItem', item.id], item);
        router.push({ pathname: '/(doctor)/case/[cid]', params: { cid: item.id } });
      }} />} />
  );
}

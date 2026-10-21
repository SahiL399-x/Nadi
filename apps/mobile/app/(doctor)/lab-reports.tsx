import { useState } from 'react';
import { Text, View } from 'react-native';
import { FlashList } from '@shopify/flash-list';
import { Card } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Skeleton } from '@/components/ui/Skeleton';
import { FilterChips } from '@/components/FilterChips';
import { useLabReports } from '@/features/doctor/useDoctorLists';
import { colors, spacing, type as t } from '@/theme/tokens';

const OPTS = [{ label: 'All', value: 'all' }, { label: 'Pending', value: 'pending' }, { label: 'Completed', value: 'completed' }];

export default function LabReports() {
  const [status, setStatus] = useState<'all' | 'pending' | 'completed'>('all');
  const { data, isLoading, isError, refetch } = useLabReports(status);
  return (
    <View style={{ flex: 1, paddingTop: spacing.lg, gap: spacing.sm }}>
      <FilterChips options={OPTS} value={status} onChange={(v) => setStatus(v as typeof status)} />
      {isLoading ? (
        <View style={{ padding: spacing.lg, gap: spacing.sm }}>{[0, 1, 2].map((i) => <Skeleton key={i} height={64} />)}</View>
      ) : isError ? <ErrorState message="Could not load lab reports." onRetry={refetch} /> : (
        <FlashList data={data ?? []} keyExtractor={(r) => r.id}
          contentContainerStyle={{ padding: spacing.lg }}
          ListEmptyComponent={<EmptyState title="No lab reports" message="Uploaded reports appear here." />}
          renderItem={({ item }) => (
            <View style={{ marginBottom: spacing.sm }}><Card>
              <Text style={{ fontSize: t.body, fontWeight: '700', color: colors.text }}>{item.patientName}</Text>
              <Text style={{ fontSize: t.sm, color: colors.textMuted }}>{item.date}</Text>
              <Text style={{ fontSize: t.xs, color: colors.navy, fontWeight: '700' }}>{item.status}</Text>
            </Card></View>
          )} />
      )}
    </View>
  );
}

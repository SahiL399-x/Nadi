import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { FlashList } from '@shopify/flash-list';
import { router, useLocalSearchParams } from 'expo-router';
import { DoctorCard } from '@/components/DoctorCard';
import { EmptyState, ErrorState, Skeleton } from '@/components/ui';
import { DoctorsMap } from '@/components/DoctorsMap';
import { useDoctors } from '@/features/patient/useDoctors';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function Doctors() {
  const { id, specialty } = useLocalSearchParams<{ id?: string; specialty: string }>();
  const { data, isLoading, isError, refetch } = useDoctors(specialty || undefined);
  const [map, setMap] = useState(false);
  if (isLoading) return <View style={{ padding: spacing.lg, gap: spacing.sm }}>{[0, 1, 2].map((i) => <Skeleton key={i} height={96} />)}</View>;
  if (isError) return <ErrorState message="Could not load doctors." onRetry={refetch} />;
  const doctors = data ?? [];
  return (
    <View style={{ flex: 1 }}>
      <View style={{ flexDirection: 'row', justifyContent: 'flex-end', padding: spacing.sm }}>
        <Pressable onPress={() => setMap((m) => !m)}><Text style={{ color: colors.navy, fontSize: t.sm }}>{map ? 'List' : 'Map'}</Text></Pressable>
      </View>
      {map ? <DoctorsMap doctors={doctors} />
        : <FlashList data={doctors} keyExtractor={(d) => d.id}
            contentContainerStyle={{ padding: spacing.lg }}
            ListEmptyComponent={<EmptyState title="No doctors nearby" message="Try widening your search." />}
            renderItem={({ item }) => <DoctorCard doctor={item}
              onPress={() => router.push({ pathname: '/(patient)/doctor/[did]',
                params: { did: item.id, ...(id ? { id } : {}) } })} />} />}
    </View>
  );
}

import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { FlashList } from '@shopify/flash-list';
import { router } from 'expo-router';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Skeleton } from '@/components/ui/Skeleton';
import { AppointmentRow } from '@/components/AppointmentRow';
import { useAppointments } from '@/features/doctor/useAppointments';
import { dayChips } from '@/lib/dates';
import { colors, spacing, type as t } from '@/theme/tokens';

const CHIPS = dayChips();

export default function Appointments() {
  const [iso, setIso] = useState(CHIPS[0]!.iso);
  const { data, isLoading, isError, refetch } = useAppointments(iso);
  return (
    <View style={{ flex: 1 }}>
      <View style={{ flexDirection: 'row', gap: spacing.sm, padding: spacing.lg, paddingBottom: spacing.sm }}>
        {CHIPS.map((c) => (
          <Pressable key={c.iso} onPress={() => setIso(c.iso)} style={{ paddingVertical: 8, paddingHorizontal: 16,
            borderRadius: 999, backgroundColor: iso === c.iso ? colors.navy : colors.lightGrey }}>
            <Text style={{ color: iso === c.iso ? '#fff' : colors.text, fontSize: t.sm }}>{c.label}</Text>
          </Pressable>
        ))}
      </View>
      {isLoading ? (
        <View style={{ padding: spacing.lg, gap: spacing.sm }}>{[0, 1, 2].map((i) => <Skeleton key={i} height={76} />)}</View>
      ) : isError ? (
        <ErrorState message="Could not load appointments." onRetry={refetch} />
      ) : (
        <FlashList data={data ?? []} keyExtractor={(a) => a.id}
          contentContainerStyle={{ padding: spacing.lg, paddingTop: 0 }}
          ListEmptyComponent={<EmptyState title="No appointments" message="Nothing booked for this day." />}
          renderItem={({ item }) => (
            <AppointmentRow appt={item} onPress={() =>
              router.push({ pathname: '/(doctor)/patient/[pid]', params: { pid: item.patientId } })} />
          )} />
      )}
    </View>
  );
}

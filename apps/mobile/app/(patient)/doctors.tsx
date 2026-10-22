import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { FlashList } from '@shopify/flash-list';
import { router, useLocalSearchParams } from 'expo-router';
import { List as ListIcon, MapPin } from 'lucide-react-native';
import { DoctorCard } from '@/components/DoctorCard';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Skeleton } from '@/components/ui/Skeleton';
import { DoctorsMap } from '@/components/DoctorsMap';
import { useDoctors } from '@/features/patient/useDoctors';
import { colors, radii, shadow, spacing, type as t } from '@/theme/tokens';

export default function Doctors() {
  const { id, specialty } = useLocalSearchParams<{ id?: string; specialty: string }>();
  const { data, isLoading, isError, refetch } = useDoctors(specialty || undefined);
  const [map, setMap] = useState(false);
  const doctors = data ?? [];

  const Seg = ({ active, label, icon, onPress }: { active: boolean; label: string; icon: React.ReactNode; onPress: () => void }) => (
    <Pressable onPress={onPress} style={{ flexDirection: 'row', alignItems: 'center', gap: 6, paddingVertical: 8,
      paddingHorizontal: spacing.md, borderRadius: radii.pill, backgroundColor: active ? colors.brightGreen : 'transparent' }}>
      {icon}
      <Text style={{ fontSize: t.sm, fontWeight: '700', color: active ? colors.white : colors.textMuted }}>{label}</Text>
    </Pressable>
  );

  return (
    <View style={{ flex: 1, backgroundColor: colors.pageBg }}>
      <View style={{ padding: spacing.lg, paddingBottom: spacing.sm, gap: spacing.sm }}>
        <Text style={{ fontSize: t.h2, fontWeight: '800', color: colors.text }}>{specialty || 'All doctors'}</Text>
        <Text style={{ fontSize: t.sm, color: colors.textMuted }}>{doctors.length} available near you</Text>
        <View style={{ flexDirection: 'row', alignSelf: 'flex-start', backgroundColor: colors.surface,
          borderRadius: radii.pill, padding: 4, ...shadow.card }}>
          <Seg active={!map} label="List" icon={<ListIcon size={16} color={!map ? colors.white : colors.textMuted} />} onPress={() => setMap(false)} />
          <Seg active={map} label="Map" icon={<MapPin size={16} color={map ? colors.white : colors.textMuted} />} onPress={() => setMap(true)} />
        </View>
      </View>

      {isLoading ? (
        <View style={{ padding: spacing.lg, gap: spacing.md }}>{[0, 1, 2].map((i) => <Skeleton key={i} height={132} />)}</View>
      ) : isError ? (
        <ErrorState message="Could not load doctors." onRetry={refetch} />
      ) : map ? (
        <DoctorsMap doctors={doctors} />
      ) : (
        <FlashList
          data={doctors}
          keyExtractor={(d) => d.id}
          contentContainerStyle={{ padding: spacing.lg, paddingTop: spacing.xs }}
          ListEmptyComponent={<EmptyState title="No doctors nearby" message="Try widening your search." />}
          renderItem={({ item }) => (
            <DoctorCard
              doctor={item}
              onPress={() => router.push({ pathname: '/(patient)/doctor/[did]', params: { did: item.id, ...(id ? { id } : {}) } })}
            />
          )}
        />
      )}
    </View>
  );
}

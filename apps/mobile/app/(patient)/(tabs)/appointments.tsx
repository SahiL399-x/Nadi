import { useQuery } from '@tanstack/react-query';
import { ScrollView, Text, View } from 'react-native';
import { router } from 'expo-router';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';
import { getMyAppointments } from '@/api/me';
import { colors, radii, shadow, spacing, type as t } from '@/theme/tokens';

export default function Appointments() {
  const { data, isLoading } = useQuery({
    queryKey: ['myAppointments'], queryFn: getMyAppointments, refetchInterval: 5000,
  });
  const items = data ?? [];
  return (
    <ScrollView style={{ backgroundColor: colors.pageBg }} contentContainerStyle={{ padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xxl }}>
      <Text style={{ fontSize: t.h2, fontWeight: '800', color: colors.text }}>My Appointments</Text>
      {isLoading ? (
        <Skeleton height={120} />
      ) : items.length === 0 ? (
        <EmptyState title="No appointments yet" message="Book a doctor and your video consultation shows up here." />
      ) : (
        items.map((a) => (
          <View key={a.consultationId} style={{ backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.lg, gap: spacing.sm, ...shadow.card }}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
              <Text style={{ fontSize: t.body, fontWeight: '800', color: colors.text }}>{a.doctorName}</Text>
              <View style={{ backgroundColor: colors.greenTint, borderRadius: radii.pill, paddingHorizontal: 10, paddingVertical: 3 }}>
                <Text style={{ fontSize: t.xs, color: colors.green700, fontWeight: '800' }}>{a.status}</Text>
              </View>
            </View>
            <Text style={{ fontSize: t.sm, color: colors.textMuted }}>{a.specialty}{a.slot ? ` · ${a.slot}` : ''}</Text>
            <Button title="Join video consultation" color={colors.brightGreen}
              onPress={() => router.push({ pathname: '/(patient)/consultation', params: { id: a.consultationId } })} />
          </View>
        ))
      )}
    </ScrollView>
  );
}

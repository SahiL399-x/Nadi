import { useQuery } from '@tanstack/react-query';
import { Pressable, ScrollView, Text, View } from 'react-native';
import { router } from 'expo-router';
import { FileText } from 'lucide-react-native';
import { EmptyState } from '@/components/ui/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';
import { getMyPrescriptions } from '@/api/me';
import { useNotifyOnNew } from '@/features/notifications/useNotifyOnNew';
import { colors, radii, shadow, spacing, type as t } from '@/theme/tokens';

export default function Prescriptions() {
  const { data, isLoading } = useQuery({
    queryKey: ['myPrescriptions'], queryFn: getMyPrescriptions, refetchInterval: 5000,
  });
  useNotifyOnNew(data, (p) => p.id, 'patient',
    (p) => ({ title: 'Prescription ready', body: `${p.doctorName} prescribed ${p.items} medicine(s).` }));
  const items = data ?? [];
  return (
    <ScrollView style={{ backgroundColor: colors.pageBg }} contentContainerStyle={{ padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xxl }}>
      <Text style={{ fontSize: t.h2, fontWeight: '800', color: colors.text }}>My Prescriptions</Text>
      {isLoading ? (
        <Skeleton height={90} />
      ) : items.length === 0 ? (
        <EmptyState title="No prescriptions yet" message="After a consultation, your prescriptions appear here." />
      ) : (
        items.map((p) => (
          <Pressable key={p.id} onPress={() => router.push({ pathname: '/(patient)/prescription', params: { id: p.id } })}
            style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.md, backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.lg, ...shadow.card }}>
            <View style={{ width: 44, height: 44, borderRadius: 22, backgroundColor: colors.greenTint, alignItems: 'center', justifyContent: 'center' }}>
              <FileText size={22} color={colors.brightGreen} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={{ fontSize: t.body, fontWeight: '700', color: colors.text }}>{p.doctorName}</Text>
              <Text style={{ fontSize: t.sm, color: colors.textMuted }}>{p.items} medicine(s) · {p.status}</Text>
            </View>
          </Pressable>
        ))
      )}
    </ScrollView>
  );
}

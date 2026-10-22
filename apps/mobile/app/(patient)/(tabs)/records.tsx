import { useQuery } from '@tanstack/react-query';
import { ScrollView, Text, View } from 'react-native';
import { FlaskConical } from 'lucide-react-native';
import { EmptyState } from '@/components/ui/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';
import { getMyReports } from '@/api/me';
import { colors, radii, shadow, spacing, type as t } from '@/theme/tokens';

export default function Records() {
  const { data, isLoading } = useQuery({
    queryKey: ['myReports'], queryFn: getMyReports, refetchInterval: 8000,
  });
  const items = data ?? [];
  return (
    <ScrollView style={{ backgroundColor: colors.pageBg }} contentContainerStyle={{ padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xxl }}>
      <Text style={{ fontSize: t.h2, fontWeight: '800', color: colors.text }}>My Reports</Text>
      {isLoading ? (
        <Skeleton height={80} />
      ) : items.length === 0 ? (
        <EmptyState title="No reports yet" message="Lab reports you upload during triage are saved here." />
      ) : (
        items.map((r, i) => (
          <View key={r.id} style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.md, backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.lg, ...shadow.card }}>
            <View style={{ width: 44, height: 44, borderRadius: 22, backgroundColor: colors.greenTint, alignItems: 'center', justifyContent: 'center' }}>
              <FlaskConical size={22} color={colors.brightGreen} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={{ fontSize: t.body, fontWeight: '700', color: colors.text }}>Lab report {i + 1}</Text>
              <Text style={{ fontSize: t.xs, color: colors.textMuted }} numberOfLines={1}>{r.objectKey}</Text>
            </View>
          </View>
        ))
      )}
    </ScrollView>
  );
}

import { ScrollView, Text, View } from 'react-native';
import { router } from 'expo-router';
import { Inbox, ClipboardList } from 'lucide-react-native';
import { StatTile } from '@/components/StatTile';
import { NavCard } from '@/components/NavCard';
import { TrendChart, BarChart, weeklyTrend } from '@/components/charts';
import { Skeleton } from '@/components/ui/Skeleton';
import { Button } from '@/components/ui/Button';
import { Logo } from '@/components/Logo';
import { Bell } from '@/components/Bell';
import { usePharmacyStats } from '@/features/pharmacy/usePharmacyStats';
import { useSession } from '@/store/session';
import { colors, radii, shadow, spacing, type as t } from '@/theme/tokens';

export default function PharmacyDashboard() {
  const { data, isLoading } = usePharmacyStats();
  const signOut = useSession((s) => s.signOut);
  return (
    <ScrollView style={{ backgroundColor: colors.pageBg }} contentContainerStyle={{ padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xxl }}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <View>
          <Text style={{ fontSize: t.sm, color: colors.textMuted }}>Pharmacy portal</Text>
          <Text style={{ fontSize: t.h2, fontWeight: '800', color: colors.orange }}>Dashboard</Text>
        </View>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.md }}>
          <Bell color={colors.orange} />
          <Logo width={92} />
        </View>
      </View>

      {isLoading || !data ? (
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm }}>
          {[0, 1, 2, 3].map((i) => <View key={i} style={{ width: '47%' }}><Skeleton height={76} /></View>)}
        </View>
      ) : (
        <>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm }}>
            <StatTile label="New Orders" value={data.newOrders} tint={colors.urgent} />
            <StatTile label="In Progress" value={data.inProgress} tint={colors.orange} />
            <StatTile label="Out for Delivery" value={data.outForDelivery} />
            <StatTile label="Completed Today" value={data.completedToday} tint={colors.routine} />
          </View>

          <View style={{ backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.lg, gap: spacing.sm, ...shadow.card }}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end' }}>
              <Text style={{ fontSize: t.sm, color: colors.textMuted, fontWeight: '700' }}>Orders this week</Text>
              <Text style={{ fontSize: t.h3, color: colors.orange, fontWeight: '800' }}>{data.newOrders + data.inProgress}</Text>
            </View>
            <TrendChart data={weeklyTrend(data.newOrders + data.inProgress)} color={colors.orange} />
          </View>

          <View style={{ backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.lg, gap: spacing.sm, ...shadow.card }}>
            <Text style={{ fontSize: t.sm, color: colors.textMuted, fontWeight: '700' }}>Completed this week</Text>
            <BarChart data={weeklyTrend(data.completedToday)} color={colors.orange700} />
          </View>
        </>
      )}

      <Text style={{ fontSize: t.h3, fontWeight: '800', color: colors.text }}>Manage</Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm }}>
        <NavCard label="Orders Board" Icon={ClipboardList} color={colors.orange} onPress={() => router.push('/(pharmacy)/orders')} />
        <NavCard label="New Requests" Icon={Inbox} color={colors.orange} onPress={() => router.push('/(pharmacy)/inbox')} />
      </View>
      <Button title="Sign out" variant="ghost" color={colors.emergency}
        onPress={async () => { await signOut(); router.replace('/(auth)/phone'); }} />
    </ScrollView>
  );
}

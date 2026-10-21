import { ScrollView, Text, View } from 'react-native';
import { router } from 'expo-router';
import { Inbox, ClipboardList } from 'lucide-react-native';
import { StatTile } from '@/components/StatTile';
import { NavCard } from '@/components/NavCard';
import { Skeleton } from '@/components/ui/Skeleton';
import { usePharmacyStats } from '@/features/pharmacy/usePharmacyStats';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function PharmacyDashboard() {
  const { data, isLoading } = usePharmacyStats();
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.h2, fontWeight: '800', color: colors.navy }}>Pharmacy</Text>
      {isLoading || !data ? (
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm }}>
          {[0, 1, 2, 3].map((i) => <View key={i} style={{ width: '47%' }}><Skeleton height={76} /></View>)}
        </View>
      ) : (
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm }}>
          <StatTile label="New Orders" value={data.newOrders} tint={colors.urgent} />
          <StatTile label="In Progress" value={data.inProgress} />
          <StatTile label="Out for Delivery" value={data.outForDelivery} />
          <StatTile label="Completed Today" value={data.completedToday} tint={colors.routine} />
        </View>
      )}
      <Text style={{ fontSize: t.h3, fontWeight: '700', color: colors.text }}>Manage</Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm }}>
        <NavCard label="Orders Board" Icon={ClipboardList} onPress={() => router.push('/(pharmacy)/orders')} />
        <NavCard label="New Requests" Icon={Inbox} onPress={() => router.push('/(pharmacy)/inbox')} />
      </View>
    </ScrollView>
  );
}

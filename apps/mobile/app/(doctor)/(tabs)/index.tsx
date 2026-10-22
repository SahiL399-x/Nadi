import { ScrollView, Text, View } from 'react-native';
import { router } from 'expo-router';
import { ListChecks, CalendarDays, FileText, FlaskConical, Clock, UserCog } from 'lucide-react-native';
import { StatTile } from '@/components/StatTile';
import { NavCard } from '@/components/NavCard';
import { TrendChart, BarChart, weeklyTrend } from '@/components/charts';
import { Skeleton } from '@/components/ui/Skeleton';
import { Button } from '@/components/ui/Button';
import { Logo } from '@/components/Logo';
import { Bell } from '@/components/Bell';
import { useDoctorStats } from '@/features/doctor/useDoctorStats';
import { useSession } from '@/store/session';
import { colors, radii, shadow, spacing, type as t } from '@/theme/tokens';

export default function DoctorDashboard() {
  const { data, isLoading } = useDoctorStats();
  const signOut = useSession((s) => s.signOut);
  return (
    <ScrollView style={{ backgroundColor: colors.pageBg }} contentContainerStyle={{ padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xxl }}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <View>
          <Text style={{ fontSize: t.sm, color: colors.textMuted }}>Doctor portal</Text>
          <Text style={{ fontSize: t.h2, fontWeight: '800', color: colors.navy }}>Dashboard</Text>
        </View>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.md }}>
          <Bell color={colors.navy} />
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
            <StatTile label="Appointments Today" value={data.appointmentsToday} />
            <StatTile label="Pending" value={data.pending} tint={colors.urgent} />
            <StatTile label="Completed" value={data.completed} tint={colors.routine} />
            <StatTile label="Prescriptions Issued" value={data.prescriptionsIssued} />
            <StatTile label="New Patients" value={data.newPatients} />
          </View>

          <View style={{ backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.lg, gap: spacing.sm, ...shadow.card }}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end' }}>
              <Text style={{ fontSize: t.sm, color: colors.textMuted, fontWeight: '700' }}>Appointments this week</Text>
              <Text style={{ fontSize: t.h3, color: colors.navy, fontWeight: '800' }}>{data.appointmentsToday}</Text>
            </View>
            <TrendChart data={weeklyTrend(data.appointmentsToday)} color={colors.navy} />
          </View>

          <View style={{ backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.lg, gap: spacing.sm, ...shadow.card }}>
            <Text style={{ fontSize: t.sm, color: colors.textMuted, fontWeight: '700' }}>Prescriptions this week</Text>
            <BarChart data={weeklyTrend(data.prescriptionsIssued)} color={colors.navy600} />
          </View>
        </>
      )}

      <Text style={{ fontSize: t.h3, fontWeight: '800', color: colors.text }}>Manage</Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm }}>
        <NavCard label="Live Queue" Icon={ListChecks} color={colors.navy} onPress={() => router.push('/(doctor)/queue')} />
        <NavCard label="Appointments" Icon={CalendarDays} color={colors.navy} onPress={() => router.push('/(doctor)/appointments')} />
        <NavCard label="Prescriptions" Icon={FileText} color={colors.navy} onPress={() => router.push('/(doctor)/prescriptions')} />
        <NavCard label="Lab Reports" Icon={FlaskConical} color={colors.navy} onPress={() => router.push('/(doctor)/lab-reports')} />
        <NavCard label="Availability" Icon={Clock} color={colors.navy} onPress={() => router.push('/(doctor)/availability')} />
        <NavCard label="Profile" Icon={UserCog} color={colors.navy} onPress={() => router.push('/(doctor)/profile')} />
      </View>
      <Button title="Sign out" variant="ghost" color={colors.emergency}
        onPress={async () => { await signOut(); router.replace('/(auth)/phone'); }} />
    </ScrollView>
  );
}

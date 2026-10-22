import { ScrollView, Text, View } from 'react-native';
import { router } from 'expo-router';
import { ListChecks, CalendarDays, FileText, FlaskConical, Clock, UserCog } from 'lucide-react-native';
import { StatTile } from '@/components/StatTile';
import { NavCard } from '@/components/NavCard';
import { Skeleton } from '@/components/ui/Skeleton';
import { Button } from '@/components/ui/Button';
import { useDoctorStats } from '@/features/doctor/useDoctorStats';
import { useSession } from '@/store/session';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function DoctorDashboard() {
  const { data, isLoading } = useDoctorStats();
  const signOut = useSession((s) => s.signOut);
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.h2, fontWeight: '800', color: colors.navy }}>Dashboard</Text>
      {isLoading || !data ? (
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm }}>
          {[0, 1, 2, 3].map((i) => <View key={i} style={{ width: '47%' }}><Skeleton height={76} /></View>)}
        </View>
      ) : (
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm }}>
          <StatTile label="Appointments Today" value={data.appointmentsToday} />
          <StatTile label="Pending" value={data.pending} tint={colors.urgent} />
          <StatTile label="Completed" value={data.completed} tint={colors.routine} />
          <StatTile label="Prescriptions Issued" value={data.prescriptionsIssued} />
          <StatTile label="New Patients" value={data.newPatients} />
        </View>
      )}
      <Text style={{ fontSize: t.h3, fontWeight: '700', color: colors.text }}>Manage</Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm }}>
        <NavCard label="Live Queue" Icon={ListChecks} onPress={() => router.push('/(doctor)/queue')} />
        <NavCard label="Appointments" Icon={CalendarDays} onPress={() => router.push('/(doctor)/appointments')} />
        <NavCard label="Prescriptions" Icon={FileText} onPress={() => router.push('/(doctor)/prescriptions')} />
        <NavCard label="Lab Reports" Icon={FlaskConical} onPress={() => router.push('/(doctor)/lab-reports')} />
        <NavCard label="Availability" Icon={Clock} onPress={() => router.push('/(doctor)/availability')} />
        <NavCard label="Profile" Icon={UserCog} onPress={() => router.push('/(doctor)/profile')} />
      </View>
      <Button title="Sign out" variant="ghost" onPress={async () => { await signOut(); router.replace('/(auth)/phone'); }} />
    </ScrollView>
  );
}

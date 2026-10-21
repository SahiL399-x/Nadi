import { ScrollView, Switch, Text, View } from 'react-native';
import { router } from 'expo-router';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Skeleton } from '@/components/ui/Skeleton';
import { useAvailability } from '@/features/doctor/useAvailability';
import { colors, spacing, type as t } from '@/theme/tokens';

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export default function AvailabilityScreen() {
  const { week, isLoading, toggle, setField, save, saving } = useAvailability();
  if (isLoading) return <View style={{ padding: spacing.lg, gap: spacing.sm }}>{[0, 1, 2].map((i) => <Skeleton key={i} height={88} />)}</View>;
  const save2 = async () => { await save(); router.back(); };
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.h2, fontWeight: '700', color: colors.text }}>Availability</Text>
      {week.map((d) => (
        <Card key={d.weekday}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text style={{ fontSize: t.body, fontWeight: '700', color: colors.text }}>{DAYS[d.weekday] ?? `Day ${d.weekday}`}</Text>
            <Switch value={d.isOpen} onValueChange={() => toggle(d.weekday)} />
          </View>
          {d.isOpen ? (
            <>
              <View style={{ height: spacing.sm }} />
              <Input value={d.morning} onChangeText={(v) => setField(d.weekday, 'morning', v)} placeholder="Morning e.g. 09:00-13:00" />
              <View style={{ height: spacing.sm }} />
              <Input value={d.evening} onChangeText={(v) => setField(d.weekday, 'evening', v)} placeholder="Evening e.g. 17:00-20:00" />
            </>
          ) : null}
        </Card>
      ))}
      <Button title="Save availability" color={colors.navy} loading={saving} onPress={save2} />
    </ScrollView>
  );
}

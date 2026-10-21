import { Linking, ScrollView, Text, View } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { router } from 'expo-router';
import { AcuityBadge, Button, Card, Skeleton } from '@/components/ui';
import { useTriage } from '@/features/patient/useTriage';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function Result() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data, isLoading } = useTriage(id!);
  if (isLoading || !data) return <View style={{ padding: spacing.lg, gap: spacing.md }}><Skeleton height={32} /><Skeleton height={120} /></View>;

  if (data.redFlags.length > 0) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.emergency, padding: spacing.xl, justifyContent: 'center', gap: spacing.lg }}>
        <Text style={{ color: '#fff', fontSize: t.h1, fontWeight: '800' }}>Seek care now</Text>
        <Text style={{ color: '#fff', fontSize: t.body }}>{data.redFlags[0]}</Text>
        <Button title="Call 108 (ambulance)" onPress={() => Linking.openURL('tel:108')} />
      </View>
    );
  }

  const top = data.specialties[0];
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <AcuityBadge acuity={data.acuity} />
      <Text style={{ fontSize: t.h2, color: colors.text, fontWeight: '700' }}>
        We suggest seeing a {top?.name ?? 'doctor'}
      </Text>
      <Card>
        <Text style={{ fontSize: t.sm, color: colors.textMuted, marginBottom: spacing.xs }}>Why we think this</Text>
        {data.drivers.map((d, i) => (
          <Text key={i} style={{ fontSize: t.sm, color: colors.text }}>• {d.feature}</Text>
        ))}
      </Card>
      {data.labs.length > 0 ? (
        <Card>
          <Text style={{ fontSize: t.sm, color: colors.textMuted }}>From your reports</Text>
          {data.labs.map((l, i) => (
            <Text key={i} style={{ fontSize: t.sm, color: l.flag === 'N' ? colors.text : colors.urgent }}>
              {l.analyte}: {l.value} {l.unit} ({l.flag})
            </Text>
          ))}
        </Card>
      ) : null}
      <Button title="See doctors" onPress={() => router.push({ pathname: '/(patient)/doctors',
        params: { id: id!, specialty: top?.name ?? '' } })} />
    </ScrollView>
  );
}

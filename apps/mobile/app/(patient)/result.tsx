import { ScrollView, Text, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Stethoscope } from 'lucide-react-native';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { useTriage } from '@/features/patient/useTriage';
import { colors, radii, shadow, spacing, type as t } from '@/theme/tokens';

export default function Result() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data, isLoading } = useTriage(id!);
  if (isLoading || !data) {
    return <View style={{ padding: spacing.lg, gap: spacing.md }}><Skeleton height={40} /><Skeleton height={140} /></View>;
  }

  const top = data.specialties[0];
  return (
    <ScrollView style={{ backgroundColor: colors.pageBg }} contentContainerStyle={{ padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xxl }}>
      <View style={{ backgroundColor: colors.greenTint, borderRadius: radii.xl, padding: spacing.lg, gap: spacing.sm, ...shadow.card }}>
        <View style={{ width: 52, height: 52, borderRadius: 26, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center' }}>
          <Stethoscope size={26} color={colors.brightGreen} />
        </View>
        <Text style={{ fontSize: t.sm, color: colors.green700, fontWeight: '700' }}>We suggest seeing a</Text>
        <Text style={{ fontSize: t.h1, color: colors.text, fontWeight: '800' }}>{top?.name ?? 'doctor'}</Text>
      </View>

      {data.labs.length > 0 ? (
        <View style={{ backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.lg, gap: spacing.xs, ...shadow.card }}>
          <Text style={{ fontSize: t.sm, color: colors.textMuted, fontWeight: '700' }}>From your reports</Text>
          {data.labs.map((l, i) => (
            <Text key={i} style={{ fontSize: t.sm, color: l.flag === 'N' ? colors.text : colors.urgent }}>
              {l.analyte}: {l.value} {l.unit} ({l.flag})
            </Text>
          ))}
        </View>
      ) : null}

      <Button title="See doctors" color={colors.brightGreen}
        onPress={() => router.push({ pathname: '/(patient)/doctors', params: { id: id!, specialty: top?.name ?? '' } })} />
      <Text style={{ fontSize: t.xs, color: colors.textFaint, textAlign: 'center' }}>
        Nadi routes you to the right doctor — it does not diagnose.
      </Text>
    </ScrollView>
  );
}

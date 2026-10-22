import { Linking, Pressable, ScrollView, Text, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { AlertTriangle, Phone, Stethoscope } from 'lucide-react-native';
import { AcuityBadge } from '@/components/ui/AcuityBadge';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { useTriage } from '@/features/patient/useTriage';
import { colors, radii, shadow, spacing, type as t } from '@/theme/tokens';

const humanize = (s: string) => s.replace(/_/g, ' ');

export default function Result() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data, isLoading } = useTriage(id!);
  if (isLoading || !data) {
    return <View style={{ padding: spacing.lg, gap: spacing.md }}><Skeleton height={40} /><Skeleton height={140} /></View>;
  }

  // SAFETY: any red flag short-circuits to the emergency screen before anything else.
  if (data.redFlags.length > 0) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.emergency, padding: spacing.xl, justifyContent: 'center', gap: spacing.lg }}>
        <AlertTriangle size={56} color={colors.white} />
        <Text style={{ color: colors.white, fontSize: t.h1, fontWeight: '800' }}>Seek care now</Text>
        <Text style={{ color: colors.white, fontSize: t.body, opacity: 0.95 }}>{data.redFlags[0]}</Text>
        <Text style={{ color: colors.white, fontSize: t.sm, opacity: 0.85 }}>
          This may be an emergency. Call an ambulance or go to the nearest hospital.
        </Text>
        <Pressable onPress={() => Linking.openURL('tel:108')}
          style={{ height: 56, borderRadius: radii.md, backgroundColor: colors.white, flexDirection: 'row',
            alignItems: 'center', justifyContent: 'center', gap: spacing.sm }}>
          <Phone size={20} color={colors.emergency} />
          <Text style={{ color: colors.emergency, fontSize: t.body, fontWeight: '800' }}>Call 108 (ambulance)</Text>
        </Pressable>
      </View>
    );
  }

  const top = data.specialties[0];
  return (
    <ScrollView style={{ backgroundColor: colors.pageBg }} contentContainerStyle={{ padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xxl }}>
      <View style={{ alignSelf: 'flex-start' }}><AcuityBadge acuity={data.acuity} /></View>

      <View style={{ backgroundColor: colors.greenTint, borderRadius: radii.xl, padding: spacing.lg, gap: spacing.sm, ...shadow.card }}>
        <View style={{ width: 52, height: 52, borderRadius: 26, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center' }}>
          <Stethoscope size={26} color={colors.brightGreen} />
        </View>
        <Text style={{ fontSize: t.sm, color: colors.green700, fontWeight: '700' }}>We suggest seeing a</Text>
        <Text style={{ fontSize: t.h1, color: colors.text, fontWeight: '800' }}>{top?.name ?? 'doctor'}</Text>
      </View>

      <View style={{ backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.lg, gap: spacing.sm, ...shadow.card }}>
        <Text style={{ fontSize: t.sm, color: colors.textMuted, fontWeight: '700' }}>Why we think this</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.xs }}>
          {data.drivers.map((d, i) => (
            <View key={i} style={{ backgroundColor: colors.lightGrey, borderRadius: radii.pill, paddingHorizontal: spacing.md, paddingVertical: 6 }}>
              <Text style={{ fontSize: t.sm, color: colors.text }}>{humanize(d.feature)}</Text>
            </View>
          ))}
        </View>
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

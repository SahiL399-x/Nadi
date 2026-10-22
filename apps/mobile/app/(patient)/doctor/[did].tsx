import { useState } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';
import { Image } from 'expo-image';
import { router, useLocalSearchParams } from 'expo-router';
import { BadgeCheck, Star } from 'lucide-react-native';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { useDoctor } from '@/features/patient/useDoctor';
import { useBook } from '@/features/patient/useBook';
import { ensureConsultation } from '@/api/patient';
import { colors, radii, shadow, spacing, type as t } from '@/theme/tokens';

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <View style={{ flex: 1, backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.md, alignItems: 'center', gap: 2, ...shadow.card }}>
      <Text style={{ fontSize: t.h3, fontWeight: '800', color: colors.text }}>{value}</Text>
      <Text style={{ fontSize: t.xs, color: colors.textMuted }}>{label}</Text>
    </View>
  );
}

export default function DoctorDetail() {
  const { did, id } = useLocalSearchParams<{ did: string; id?: string }>();
  const { data: d, isLoading } = useDoctor(did!);
  const { confirm, pending } = useBook();
  const [slot, setSlot] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  if (isLoading || !d) return <View style={{ padding: spacing.lg }}><Skeleton height={220} /></View>;
  const bookNow = async () => {
    if (!slot) return;
    setBusy(true);
    try {
      const cid = await ensureConsultation(id, d.specialty);
      const ok = await confirm(cid, d.id, slot);
      if (ok) router.replace({ pathname: '/(patient)/booked', params: { id: cid, slot, name: d.name } });
    } finally { setBusy(false); }
  };
  return (
    <View style={{ flex: 1, backgroundColor: colors.pageBg }}>
      <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md, paddingBottom: 120 }}>
        <View style={{ backgroundColor: colors.surface, borderRadius: radii.xl, padding: spacing.lg, alignItems: 'center', gap: spacing.sm, ...shadow.card }}>
          <Image source={d.photoUrl ? { uri: d.photoUrl } : undefined}
            style={{ width: 104, height: 104, borderRadius: 52, backgroundColor: colors.greenTint }} contentFit="cover" transition={200} />
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
            <Text style={{ fontSize: t.h2, fontWeight: '800', color: colors.text }}>{d.name}</Text>
            <BadgeCheck size={18} color={colors.brightGreen} />
          </View>
          <Text style={{ fontSize: t.sm, color: colors.textMuted }}>{d.specialty} · {d.qualifications}</Text>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: colors.greenTint,
            borderRadius: radii.pill, paddingHorizontal: 10, paddingVertical: 4 }}>
            <Star size={13} color={colors.green700} fill={colors.green700} />
            <Text style={{ fontSize: t.sm, color: colors.green700, fontWeight: '800' }}>{d.rating}</Text>
            <Text style={{ fontSize: t.xs, color: colors.green700 }}>· {d.reviewCount} stories</Text>
          </View>
        </View>

        <View style={{ flexDirection: 'row', gap: spacing.sm }}>
          <Stat label="Experience" value={`${d.experienceYears}y`} />
          <Stat label="Consult fee" value={`₹${d.feeInr}`} />
          <Stat label="Distance" value={`${d.distanceKm}km`} />
        </View>

        <View style={{ backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.lg, gap: spacing.sm, ...shadow.card }}>
          <Text style={{ fontSize: t.sm, color: colors.textMuted, fontWeight: '700' }}>Speaks</Text>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.xs }}>
            {d.languages.map((l) => (
              <View key={l} style={{ backgroundColor: colors.lightGrey, borderRadius: radii.pill, paddingHorizontal: 12, paddingVertical: 6 }}>
                <Text style={{ fontSize: t.sm, color: colors.text }}>{l}</Text>
              </View>
            ))}
          </View>
        </View>

        <Text style={{ fontSize: t.h3, fontWeight: '800', color: colors.text }}>Pick a time slot</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm }}>
          {d.availableSlots.map((s) => (
            <Pressable key={s} onPress={() => setSlot(s)}
              style={{ paddingVertical: 10, paddingHorizontal: spacing.md, borderRadius: radii.md,
                backgroundColor: slot === s ? colors.brightGreen : colors.surface,
                borderWidth: 1, borderColor: slot === s ? colors.brightGreen : colors.border }}>
              <Text style={{ fontSize: t.sm, fontWeight: '700', color: slot === s ? colors.white : colors.text }}>{s}</Text>
            </Pressable>
          ))}
        </View>
      </ScrollView>

      <View style={{ padding: spacing.lg, backgroundColor: colors.surface, borderTopWidth: 1, borderColor: colors.border }}>
        <Button title={slot ? `Book ${slot}` : 'Select a slot'} color={colors.brightGreen}
          onPress={bookNow} loading={busy || pending} disabled={!slot || busy} />
      </View>
    </View>
  );
}

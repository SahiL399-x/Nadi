import { Pressable, Text, View } from 'react-native';
import { Image } from 'expo-image';
import { BadgeCheck, MapPin, Star } from 'lucide-react-native';
import type { Doctor } from '@/api/schemas';
import { colors, radii, shadow, spacing, type as t } from '@/theme/tokens';

export function DoctorCard({ doctor, onPress }: { doctor: Doctor; onPress: () => void }) {
  return (
    <Pressable
      onPress={onPress}
      style={{ marginBottom: spacing.md, backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.md, ...shadow.card }}
    >
      <View style={{ flexDirection: 'row', gap: spacing.md }}>
        <Image
          source={doctor.photoUrl ? { uri: doctor.photoUrl } : undefined}
          style={{ width: 76, height: 76, borderRadius: radii.md, backgroundColor: colors.greenTint }}
          contentFit="cover"
          transition={200}
        />
        <View style={{ flex: 1, gap: 2 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
            <Text style={{ fontSize: t.body, fontWeight: '800', color: colors.text, flexShrink: 1 }} numberOfLines={1}>
              {doctor.name}
            </Text>
            <BadgeCheck size={16} color={colors.brightGreen} />
          </View>
          <Text style={{ fontSize: t.sm, color: colors.textMuted }} numberOfLines={1}>
            {doctor.specialty} · {doctor.qualifications}
          </Text>
          <Text style={{ fontSize: t.sm, color: colors.text, fontWeight: '600' }}>
            {doctor.experienceYears} yrs experience
          </Text>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.sm, marginTop: 2 }}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 3, backgroundColor: colors.greenTint,
              borderRadius: radii.sm, paddingHorizontal: 6, paddingVertical: 2 }}>
              <Star size={12} color={colors.green700} fill={colors.green700} />
              <Text style={{ fontSize: t.xs, color: colors.green700, fontWeight: '800' }}>{doctor.rating}</Text>
            </View>
            <Text style={{ fontSize: t.xs, color: colors.textMuted }}>{doctor.reviewCount} stories</Text>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 2 }}>
              <MapPin size={12} color={colors.textFaint} />
              <Text style={{ fontSize: t.xs, color: colors.textMuted }}>{doctor.distanceKm} km</Text>
            </View>
          </View>
        </View>
      </View>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
        marginTop: spacing.sm, paddingTop: spacing.sm, borderTopWidth: 1, borderTopColor: colors.border }}>
        <Text style={{ fontSize: t.body, color: colors.text, fontWeight: '800' }}>
          ₹{doctor.feeInr} <Text style={{ fontSize: t.sm, color: colors.textMuted, fontWeight: '400' }}>consult</Text>
        </Text>
        <View style={{ backgroundColor: colors.brightGreen, borderRadius: radii.pill, paddingHorizontal: spacing.lg, paddingVertical: 8 }}>
          <Text style={{ color: colors.white, fontSize: t.sm, fontWeight: '800' }}>Book</Text>
        </View>
      </View>
    </Pressable>
  );
}

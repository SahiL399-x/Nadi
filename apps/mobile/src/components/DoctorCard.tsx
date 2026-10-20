import { Pressable, Text, View } from 'react-native';
import { Avatar, Card } from '@/components/ui';
import type { Doctor } from '@/api/schemas';
import { colors, spacing, type as t } from '@/theme/tokens';

export function DoctorCard({ doctor, onPress }: { doctor: Doctor; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} style={{ marginBottom: spacing.sm }}>
      <Card>
        <View style={{ flexDirection: 'row', gap: spacing.md }}>
          <Avatar uri={doctor.photoUrl} />
          <View style={{ flex: 1 }}>
            <Text style={{ fontSize: t.body, fontWeight: '700', color: colors.text }}>{doctor.name}</Text>
            <Text style={{ fontSize: t.sm, color: colors.textMuted }}>{doctor.specialty} · {doctor.qualifications}</Text>
            <Text style={{ fontSize: t.sm, color: colors.textMuted }}>
              {doctor.distanceKm} km · ₹{doctor.feeInr} · ★ {doctor.rating} ({doctor.reviewCount})
            </Text>
            <Text style={{ fontSize: t.xs, color: colors.textMuted }}>{doctor.languages.join(', ')}</Text>
          </View>
        </View>
      </Card>
    </Pressable>
  );
}

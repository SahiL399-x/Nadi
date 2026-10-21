import { Pressable, Text, View } from 'react-native';
import { AcuityBadge } from '@/components/ui/AcuityBadge';
import { Card } from '@/components/ui/Card';
import type { Appointment } from '@/api/doctorPortal';
import { colors, spacing, type as t } from '@/theme/tokens';

export function AppointmentRow({ appt, onPress }: { appt: Appointment; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} style={{ marginBottom: spacing.sm }}>
      <Card>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.md }}>
          <Text style={{ fontSize: t.body, fontWeight: '800', color: colors.navy, width: 64 }}>{appt.time}</Text>
          <View style={{ flex: 1 }}>
            <Text style={{ fontSize: t.body, fontWeight: '700', color: colors.text }}>
              {appt.patientName}, {appt.patientAge}{appt.patientSex}
            </Text>
            <Text style={{ fontSize: t.sm, color: colors.textMuted }} numberOfLines={1}>{appt.complaint}</Text>
          </View>
          <View style={{ alignItems: 'flex-end', gap: 4 }}>
            <Text style={{ fontSize: t.xs, color: colors.navy, fontWeight: '700' }}>{appt.status}</Text>
            {appt.acuity ? <AcuityBadge acuity={appt.acuity} /> : null}
          </View>
        </View>
      </Card>
    </Pressable>
  );
}

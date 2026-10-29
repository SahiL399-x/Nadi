import { Image, Pressable, Text, View } from 'react-native';
import type { ReportView } from '@/api/doctorPortal';
import { colors, radii, spacing, type as t } from '@/theme/tokens';

export function ReportCard({ report, label, onOpen }: { report: ReportView; label: string; onOpen: () => void }) {
  return (
    <Pressable
      onPress={onOpen}
      style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.md, backgroundColor: colors.surface,
        borderRadius: radii.lg, borderWidth: 1, borderColor: colors.border, padding: spacing.md }}
    >
      <View style={{ flex: 1 }}>
        <Text style={{ fontSize: t.body, fontWeight: '700', color: colors.text }}>{label}</Text>
        <Text style={{ fontSize: t.xs, color: colors.textMuted }}>{report.date}</Text>
        {report.needsReview ? (
          <Text style={{ fontSize: t.xs, color: colors.emergency, fontWeight: '700' }}>Needs review</Text>
        ) : null}
      </View>
      {report.kind === 'image' ? (
        <Image testID="report-thumb" source={{ uri: report.imageUrl }}
          style={{ width: 64, height: 80, borderRadius: radii.sm }} />
      ) : (
        <View testID="report-pdf" style={{ width: 64, height: 80, borderRadius: radii.sm,
          backgroundColor: colors.greenTint, alignItems: 'center', justifyContent: 'center' }}>
          <Text style={{ fontWeight: '800', color: colors.text }}>PDF</Text>
        </View>
      )}
    </Pressable>
  );
}

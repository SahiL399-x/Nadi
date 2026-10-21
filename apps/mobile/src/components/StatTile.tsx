import { Text, View } from 'react-native';
import { Card } from '@/components/ui/Card';
import { colors, type as t } from '@/theme/tokens';

export function StatTile({ label, value, tint }: { label: string; value: number; tint?: string }) {
  return (
    <View style={{ width: '47%' }}>
      <Card>
        <Text style={{ fontSize: t.h1, fontWeight: '800', color: tint ?? colors.navy }}>{value}</Text>
        <Text style={{ fontSize: t.xs, color: colors.textMuted }}>{label}</Text>
      </Card>
    </View>
  );
}

import { Pressable, Text, View } from 'react-native';
import { Card } from '@/components/ui';
import type { QueueItem } from '@/api/schemas';
import { colors, spacing, type as t } from '@/theme/tokens';

export function QueueRow({ item, onPress }: { item: QueueItem; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} style={{ marginBottom: spacing.sm }}>
      <View style={{ borderRadius: 14 }}>
        <Card>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
            <View style={{ flex: 1 }}>
              <Text style={{ fontSize: t.body, fontWeight: '700', color: colors.text }}>
                {item.patientName}, {item.patientAge}{item.patientSex}
              </Text>
              <Text style={{ fontSize: t.sm, color: colors.textMuted }} numberOfLines={1}>{item.complaint}</Text>
            </View>
          </View>
        </Card>
      </View>
    </Pressable>
  );
}

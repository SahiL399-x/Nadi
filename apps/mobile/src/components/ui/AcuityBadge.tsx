import { Text, View } from 'react-native';
import type { Acuity } from '@nadi/shared-types';
import { acuityColor, type as t } from '@/theme/tokens';

const LABEL: Record<Acuity, string> = {
  ROUTINE: 'Routine', PRIORITY: 'Priority', URGENT: 'Urgent', EMERGENCY: 'Emergency',
};
export function AcuityBadge({ acuity }: { acuity: Acuity }) {
  return (
    <View style={{ backgroundColor: acuityColor(acuity), borderRadius: 999,
      paddingHorizontal: 12, paddingVertical: 4, alignSelf: 'flex-start' }}>
      <Text style={{ color: '#FFFFFF', fontSize: t.xs, fontWeight: '700' }}>{LABEL[acuity]}</Text>
    </View>
  );
}

import { ActivityIndicator, Pressable, Text } from 'react-native';
import { colors, radii, type as t } from '@/theme/tokens';

type Props = { title: string; onPress: () => void; variant?: 'primary' | 'ghost';
  disabled?: boolean; loading?: boolean; color?: string };

export function Button({ title, onPress, variant = 'primary', disabled, loading, color }: Props) {
  const bg = variant === 'primary' ? (color ?? colors.seaGreen) : 'transparent';
  const fg = variant === 'primary' ? '#FFFFFF' : (color ?? colors.seaGreen);
  const off = disabled || loading;
  return (
    <Pressable testID="button" accessibilityRole="button" disabled={off} onPress={onPress}
      style={{ height: 56, borderRadius: radii.md, backgroundColor: bg, opacity: off ? 0.5 : 1,
        alignItems: 'center', justifyContent: 'center', width: '100%' }}>
      {loading ? <ActivityIndicator color={fg} />
        : <Text style={{ color: fg, fontSize: t.body, fontWeight: '600' }}>{title}</Text>}
    </Pressable>
  );
}

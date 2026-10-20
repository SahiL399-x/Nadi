import { Text, View } from 'react-native';
import { Button } from '@/components/ui/Button';
import { colors, spacing, type as t } from '@/theme/tokens';
export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return <View style={{ alignItems: 'center', padding: spacing.xl, gap: spacing.md }}>
    <Text style={{ fontSize: t.body, color: colors.emergency, textAlign: 'center' }}>{message}</Text>
    <Button title="Try again" onPress={onRetry} variant="ghost" />
  </View>;
}

import { View } from 'react-native';
import { colors, radii, spacing } from '@/theme/tokens';
export function Card({ children }: { children: React.ReactNode }) {
  return <View style={{ backgroundColor: colors.surface, borderRadius: radii.md,
    borderWidth: 1, borderColor: colors.border, padding: spacing.md }}>{children}</View>;
}

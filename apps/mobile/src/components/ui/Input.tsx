import { TextInput } from 'react-native';
import { colors, radii, spacing, type as t } from '@/theme/tokens';
type Props = { value: string; onChangeText: (v: string) => void; placeholder?: string;
  keyboardType?: 'default' | 'phone-pad' | 'number-pad'; multiline?: boolean };
export function Input(p: Props) {
  return <TextInput value={p.value} onChangeText={p.onChangeText} placeholder={p.placeholder}
    keyboardType={p.keyboardType} multiline={p.multiline} placeholderTextColor={colors.textMuted}
    style={{ minHeight: 48, borderWidth: 1, borderColor: colors.border, borderRadius: radii.sm,
      paddingHorizontal: spacing.md, fontSize: t.body, color: colors.text }} />;
}

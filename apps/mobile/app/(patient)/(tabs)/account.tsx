import { Text, View } from 'react-native';
import { router } from 'expo-router';
import { Button } from '@/components/ui';
import { useSession } from '@/store/session';
import { colors, spacing, type as t } from '@/theme/tokens';
export default function Account() {
  const signOut = useSession((s) => s.signOut);
  return (
    <View style={{ flex: 1, padding: spacing.lg, gap: spacing.md, justifyContent: 'center' }}>
      <Text style={{ fontSize: t.h2, color: colors.text, fontWeight: '700' }}>Account</Text>
      <Button title="Sign out" variant="ghost" onPress={async () => { await signOut(); router.replace('/(auth)/phone'); }} />
    </View>
  );
}

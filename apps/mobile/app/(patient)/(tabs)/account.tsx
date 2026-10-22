import { Text, View } from 'react-native';
import { router } from 'expo-router';
import { User } from 'lucide-react-native';
import { Button } from '@/components/ui/Button';
import { useSession } from '@/store/session';
import { colors, radii, shadow, spacing, type as t } from '@/theme/tokens';

export default function Account() {
  const signOut = useSession((s) => s.signOut);
  return (
    <View style={{ flex: 1, backgroundColor: colors.pageBg, padding: spacing.lg, gap: spacing.lg }}>
      <View style={{ alignItems: 'center', gap: spacing.sm, marginTop: spacing.xl }}>
        <View style={{ width: 88, height: 88, borderRadius: 44, backgroundColor: colors.greenTint,
          alignItems: 'center', justifyContent: 'center' }}>
          <User size={40} color={colors.brightGreen} />
        </View>
        <Text style={{ fontSize: t.h2, color: colors.text, fontWeight: '800' }}>My Account</Text>
        <Text style={{ fontSize: t.sm, color: colors.textMuted }}>Nadi patient</Text>
      </View>
      <View style={{ backgroundColor: colors.surface, borderRadius: radii.xl, padding: spacing.lg, ...shadow.card }}>
        <Button title="Sign out" variant="ghost" color={colors.emergency}
          onPress={async () => { await signOut(); router.replace('/(auth)/phone'); }} />
      </View>
    </View>
  );
}

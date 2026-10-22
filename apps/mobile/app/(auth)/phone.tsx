import { useState } from 'react';
import { Text, View } from 'react-native';
import { router } from 'expo-router';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Logo } from '@/components/Logo';
import { requestOtp } from '@/api/auth';
import { colors, radii, shadow, spacing, type as t } from '@/theme/tokens';

export default function PhoneScreen() {
  const [phone, setPhone] = useState('+91');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submit = async () => {
    setLoading(true); setError(null);
    try { await requestOtp(phone); router.push({ pathname: '/(auth)/otp', params: { phone } }); }
    catch { setError('Could not send the code. Check your connection.'); }
    finally { setLoading(false); }
  };
  return (
    <View style={{ flex: 1, backgroundColor: colors.pageBg, padding: spacing.lg, justifyContent: 'center', gap: spacing.xl }}>
      <View style={{ alignItems: 'center', gap: spacing.xs }}>
        <Logo width={210} />
        <Text style={{ fontSize: t.body, color: colors.textMuted, textAlign: 'center' }}>
          Read your body&apos;s signals.{'\n'}Get to the right doctor.
        </Text>
      </View>
      <View style={{ backgroundColor: colors.surface, borderRadius: radii.xl, padding: spacing.lg, gap: spacing.md, ...shadow.card }}>
        <Text style={{ fontSize: t.h2, color: colors.text, fontWeight: '800' }}>Welcome</Text>
        <Text style={{ fontSize: t.sm, color: colors.textMuted }}>Enter your phone number to continue.</Text>
        <Input value={phone} onChangeText={setPhone} keyboardType="phone-pad" placeholder="+91…" />
        {error ? <Text style={{ color: colors.emergency, fontSize: t.sm }}>{error}</Text> : null}
        <Button title="Send code" onPress={submit} loading={loading} color={colors.brightGreen} />
      </View>
    </View>
  );
}

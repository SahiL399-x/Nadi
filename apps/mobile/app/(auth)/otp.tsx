import { useState } from 'react';
import { ImageBackground, Text, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Logo } from '@/components/Logo';
import { verifyOtp } from '@/api/auth';
import { useSession } from '@/store/session';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function OtpScreen() {
  const { phone } = useLocalSearchParams<{ phone: string }>();
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const signIn = useSession((s) => s.signIn);
  const submit = async () => {
    setLoading(true); setError(null);
    try {
      // New patients are created server-side with a default name — no extra step.
      const pair = await verifyOtp({ phone: phone!, code });
      await signIn(pair);
      router.replace('/');
    } catch { setError('Invalid code. Use 123456 for the demo.'); }
    finally { setLoading(false); }
  };
  return (
    <ImageBackground source={require('../../assets/login-bg.png')} style={{ flex: 1 }} resizeMode="cover">
      <View style={{ flex: 1, paddingHorizontal: spacing.lg, paddingBottom: spacing.xxl }}>
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
          <Logo width={210} />
        </View>
        <View style={{ gap: spacing.md }}>
          <Text style={{ fontSize: t.h1, color: colors.text, fontWeight: '800' }}>Enter the code</Text>
          <Text style={{ fontSize: t.sm, color: colors.textMuted }}>Sent to {phone}</Text>
          <Input value={code} onChangeText={setCode} keyboardType="number-pad" placeholder="123456" />
          {error ? <Text style={{ color: colors.emergency, fontSize: t.sm }}>{error}</Text> : null}
          <Button title="Verify & continue" onPress={submit} loading={loading} color={colors.brightGreen} />
        </View>
      </View>
    </ImageBackground>
  );
}

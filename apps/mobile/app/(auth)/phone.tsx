import { useEffect, useState } from 'react';
import { ImageBackground, Text, View } from 'react-native';
import { router } from 'expo-router';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Logo } from '@/components/Logo';
import { requestOtp } from '@/api/auth';
import { requestLocation } from '@/lib/location';
import { requestNotifications } from '@/lib/notify';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function PhoneScreen() {
  const [phone, setPhone] = useState('+91');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Ask for location + notification permission up front.
  useEffect(() => { void requestLocation(); void requestNotifications(); }, []);
  const submit = async () => {
    setLoading(true); setError(null);
    try { await requestOtp(phone); router.push({ pathname: '/(auth)/otp', params: { phone } }); }
    catch { setError('Could not send the code. Check your connection.'); }
    finally { setLoading(false); }
  };
  return (
    <ImageBackground source={require('../../assets/login-bg.png')} style={{ flex: 1 }} resizeMode="cover">
      <View style={{ flex: 1, paddingHorizontal: spacing.lg, paddingBottom: spacing.xxl }}>
        {/* Logo sits in the green clinic scene; the form sits on the white fade below. */}
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', gap: spacing.sm }}>
          <Logo width={250} />
          <Text style={{ fontSize: t.body, color: colors.green700, fontWeight: '600', textAlign: 'center' }}>
            Read your body&apos;s signals.{'\n'}Get to the right doctor.
          </Text>
        </View>
        <View style={{ gap: spacing.md }}>
          <Text style={{ fontSize: t.h1, color: colors.text, fontWeight: '800' }}>Welcome</Text>
          <Text style={{ fontSize: t.sm, color: colors.textMuted }}>Enter your phone number to continue.</Text>
          <Input value={phone} onChangeText={setPhone} keyboardType="phone-pad" placeholder="+91…" />
          {error ? <Text style={{ color: colors.emergency, fontSize: t.sm }}>{error}</Text> : null}
          <Button title="Send code" onPress={submit} loading={loading} color={colors.brightGreen} />
        </View>
      </View>
    </ImageBackground>
  );
}

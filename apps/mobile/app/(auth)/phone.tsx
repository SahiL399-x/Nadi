import { useState } from 'react';
import { Text, View } from 'react-native';
import { router } from 'expo-router';
import { Button, Input } from '@/components/ui';
import { requestOtp } from '@/api/auth';
import { colors, spacing, type as t } from '@/theme/tokens';

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
    <View style={{ flex: 1, padding: spacing.lg, gap: spacing.md, justifyContent: 'center' }}>
      <Text style={{ fontSize: t.h1, color: colors.text, fontWeight: '700' }}>Welcome to NADI</Text>
      <Text style={{ fontSize: t.sm, color: colors.textMuted }}>Enter your phone number to continue</Text>
      <Input value={phone} onChangeText={setPhone} keyboardType="phone-pad" placeholder="+91…" />
      {error ? <Text style={{ color: colors.emergency, fontSize: t.sm }}>{error}</Text> : null}
      <Button title="Send code" onPress={submit} loading={loading} />
    </View>
  );
}

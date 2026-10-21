import { useState } from 'react';
import { Text, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Button, Input } from '@/components/ui';
import { verifyOtp } from '@/api/auth';
import { useSession } from '@/store/session';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function OtpScreen() {
  const { phone } = useLocalSearchParams<{ phone: string }>();
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const signIn = useSession((s) => s.signIn);
  const submit = async () => {
    setLoading(true); setError(null);
    try {
      const pair = await verifyOtp({ phone: phone!, code, name });
      await signIn(pair);
      router.replace('/');
    } catch { setError('Invalid code. Use 123456 for the demo.'); }
    finally { setLoading(false); }
  };
  return (
    <View style={{ flex: 1, padding: spacing.lg, gap: spacing.md, justifyContent: 'center' }}>
      <Text style={{ fontSize: t.h2, color: colors.text, fontWeight: '700' }}>Enter the code</Text>
      <Text style={{ fontSize: t.sm, color: colors.textMuted }}>Sent to {phone}</Text>
      <Input value={code} onChangeText={setCode} keyboardType="number-pad" placeholder="123456" />
      <Input value={name} onChangeText={setName} placeholder="Your name (new patients)" />
      {error ? <Text style={{ color: colors.emergency, fontSize: t.sm }}>{error}</Text> : null}
      <Button title="Verify" onPress={submit} loading={loading} />
    </View>
  );
}

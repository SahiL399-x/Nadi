import { useState } from 'react';
import { ScrollView, Text } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useRefer } from '@/features/doctor/useRefer';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function Refer() {
  const { cid } = useLocalSearchParams<{ cid: string }>();
  const { submit, pending } = useRefer();
  const [spec, setSpec] = useState('');
  const [reason, setReason] = useState('');
  const save = async () => { await submit(cid!, spec, reason); router.replace('/(doctor)'); };
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.h2, fontWeight: '700', color: colors.text }}>Refer patient</Text>
      <Input value={spec} onChangeText={setSpec} placeholder="Refer to specialty (e.g. Cardiology)" />
      <Input value={reason} onChangeText={setReason} multiline placeholder="Reason" />
      <Button title="Send referral" color={colors.navy} loading={pending}
        disabled={!spec.trim() || !reason.trim()} onPress={save} />
    </ScrollView>
  );
}

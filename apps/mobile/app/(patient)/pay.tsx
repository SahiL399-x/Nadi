import { useState } from 'react';
import { ActivityIndicator, Text, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import Animated, { FadeIn, ZoomIn } from 'react-native-reanimated';
import { Check, ShieldCheck } from 'lucide-react-native';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { ensureConsultation, book } from '@/api/patient';
import { notify } from '@/lib/notify';
import { colors, radii, shadow, spacing, type as t } from '@/theme/tokens';

// Mock UPI payment: no real money moves. On "pay" we book the consultation and
// show a success check, then land on the Appointments tab.
export default function Pay() {
  const p = useLocalSearchParams<{
    amount: string; doctorId: string; slot: string; specialty?: string; doctorName?: string; id?: string;
  }>();
  const [upi, setUpi] = useState('demo@okaxis');
  const [state, setState] = useState<'form' | 'paying' | 'done'>('form');

  const pay = () => {
    setState('paying');
    setTimeout(async () => {
      try {
        const cid = await ensureConsultation(p.id || undefined, p.specialty || '');
        await book(cid, { doctorId: p.doctorId, slot: p.slot });
        void notify('patient', 'Appointment booked', `Your video consultation with ${p.doctorName ?? 'the doctor'} is confirmed.`);
        setState('done');
        setTimeout(() => router.replace('/(patient)/(tabs)/appointments'), 1700);
      } catch {
        setState('form');
      }
    }, 1500);
  };

  if (state === 'done') {
    return (
      <View style={{ flex: 1, backgroundColor: colors.pageBg, alignItems: 'center', justifyContent: 'center', gap: spacing.md, padding: spacing.xl }}>
        <Animated.View entering={ZoomIn.springify().damping(12)}
          style={{ width: 116, height: 116, borderRadius: 58, backgroundColor: colors.brightGreen, alignItems: 'center', justifyContent: 'center' }}>
          <Check size={64} color={colors.white} strokeWidth={3} />
        </Animated.View>
        <Animated.Text entering={FadeIn.delay(180)} style={{ fontSize: t.h2, fontWeight: '800', color: colors.text }}>Payment successful</Animated.Text>
        <Animated.Text entering={FadeIn.delay(300)} style={{ fontSize: t.sm, color: colors.textMuted, textAlign: 'center' }}>
          Your video consultation is booked. Opening your appointments…
        </Animated.Text>
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.pageBg, padding: spacing.lg, justifyContent: 'center', gap: spacing.lg }}>
      <View style={{ alignItems: 'center', gap: 2 }}>
        <Text style={{ fontSize: t.sm, color: colors.textMuted }}>Amount payable</Text>
        <Text style={{ fontSize: 44, fontWeight: '800', color: colors.text }}>₹{p.amount}</Text>
        {p.doctorName ? <Text style={{ fontSize: t.sm, color: colors.textMuted }}>Consultation · {p.doctorName}</Text> : null}
      </View>
      <View style={{ backgroundColor: colors.surface, borderRadius: radii.xl, padding: spacing.lg, gap: spacing.md, ...shadow.card }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.sm }}>
          <ShieldCheck size={20} color={colors.brightGreen} />
          <Text style={{ fontSize: t.sm, color: colors.text, fontWeight: '700' }}>Pay securely via UPI</Text>
        </View>
        <Input value={upi} onChangeText={setUpi} placeholder="UPI ID (e.g. name@okaxis)" />
        {state === 'paying' ? (
          <View style={{ height: 56, alignItems: 'center', justifyContent: 'center' }}>
            <ActivityIndicator color={colors.brightGreen} />
          </View>
        ) : (
          <Button title={`Pay ₹${p.amount}`} color={colors.brightGreen} onPress={pay} />
        )}
        <Text style={{ fontSize: t.xs, color: colors.textFaint, textAlign: 'center' }}>Demo payment — no real money is charged.</Text>
      </View>
    </View>
  );
}

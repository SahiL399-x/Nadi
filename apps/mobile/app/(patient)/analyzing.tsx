import { useEffect, useRef, useState } from 'react';
import { Text, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { useIntake } from '@/features/patient/useIntake';
import { useTheme } from '@/providers/ThemeProvider';
import { colors, spacing, type as t } from '@/theme/tokens';

const LINES = ['Reading your reports', 'Understanding your symptoms', 'Finding the right doctor'];

export default function Analyzing() {
  const theme = useTheme();
  const { submit } = useIntake();
  const { symptomText, lang, keys } = useLocalSearchParams<{ symptomText: string; lang: string; keys: string }>();
  const [line, setLine] = useState(0);
  const started = useRef(false);
  useEffect(() => {
    const id = setInterval(() => setLine((n) => Math.min(n + 1, LINES.length - 1)), 700);
    return () => clearInterval(id);
  }, []);
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const run = async () => {
      const consultationId = await submit({ symptomText: symptomText ?? '', lang: (lang as 'en') ?? 'en',
        reportImageUris: keys ? (JSON.parse(keys) as string[]) : [] });
      setTimeout(() => router.replace({ pathname: '/(patient)/result', params: { id: consultationId } }), 1800);
    };
    run().catch(() => router.replace('/(patient)'));
  }, [symptomText, lang, keys, submit]);
  return (
    <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', padding: spacing.xl, gap: spacing.md }}>
      <Text style={{ fontSize: t.h3, color: theme.primary, fontWeight: '600' }}>{LINES[line]}…</Text>
      <Text style={{ fontSize: t.sm, color: colors.textMuted }}>This takes a few seconds</Text>
    </View>
  );
}

import { useState } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';
import { router } from 'expo-router';
import { Button, Card, Input } from '@/components/ui';
import { SpecialtyGrid } from '@/components/SpecialtyGrid';
import { useTheme } from '@/providers/ThemeProvider';
import { colors, spacing, type as t } from '@/theme/tokens';

type Lang = 'en' | 'hi' | 'mr';
const CANNED: Record<Lang, string> = {
  en: 'I have had chest pain and breathlessness since morning',
  hi: 'subah se seene mein dard aur saans phoolne ki shikayat hai',
  mr: 'सकाळपासून छातीत दुखत आहे आणि दम लागतो आहे',
};

export default function PatientHome() {
  const theme = useTheme();
  const [text, setText] = useState('');
  const [lang, setLang] = useState<Lang>('en');
  const triage = () => router.push({ pathname: '/(patient)/reports', params: { symptomText: text, lang } });
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.lg }}>
      <Text style={{ fontSize: t.h1, color: theme.primary, fontWeight: '800' }}>NADI</Text>
      <Card>
        <Text style={{ fontSize: t.h3, color: colors.text, fontWeight: '700' }}>Tell us your problem</Text>
        <Text style={{ fontSize: t.sm, color: colors.textMuted, marginBottom: spacing.sm }}>We'll route you to the right doctor.</Text>
        <View style={{ flexDirection: 'row', gap: spacing.sm, marginBottom: spacing.sm }}>
          {(['en', 'hi', 'mr'] as Lang[]).map((l) => (
            <Pressable key={l} onPress={() => setLang(l)} style={{ paddingVertical: 6, paddingHorizontal: 14,
              borderRadius: 999, backgroundColor: lang === l ? theme.primary : colors.lightGrey }}>
              <Text style={{ color: lang === l ? '#fff' : colors.text, fontSize: t.sm }}>{l.toUpperCase()}</Text>
            </Pressable>
          ))}
        </View>
        <Input value={text} onChangeText={setText} multiline placeholder="e.g. chest pain since morning…" />
        <View style={{ height: spacing.sm }} />
        <Button title="🎤 Speak instead" variant="ghost" color={theme.primary}
          onPress={() => setTimeout(() => setText(CANNED[lang]), 2000)} />
        <View style={{ height: spacing.sm }} />
        <Button title="Find the right doctor" onPress={triage} color={theme.primary}
          disabled={text.trim().length === 0} />
      </Card>
      <Text style={{ fontSize: t.h3, color: colors.text, fontWeight: '700' }}>Find doctors by speciality</Text>
      <SpecialtyGrid onSelect={(s) => router.push({ pathname: '/(patient)/doctors', params: { specialty: s.specialty } })} />
    </ScrollView>
  );
}

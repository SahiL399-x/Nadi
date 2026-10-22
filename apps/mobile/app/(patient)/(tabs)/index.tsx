import { useState } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';
import { router } from 'expo-router';
import { Search } from 'lucide-react-native';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { SpecialtyGrid } from '@/components/SpecialtyGrid';
import { Logo } from '@/components/Logo';
import { colors, radii, shadow, spacing, type as t } from '@/theme/tokens';

type Lang = 'en' | 'hi' | 'mr';
const CANNED: Record<Lang, string> = {
  en: 'I have had chest pain and breathlessness since morning',
  hi: 'subah se seene mein dard aur saans phoolne ki shikayat hai',
  mr: 'सकाळपासून छातीत दुखत आहे आणि दम लागतो आहे',
};

export default function PatientHome() {
  const [text, setText] = useState('');
  const [lang, setLang] = useState<Lang>('en');
  const triage = () => router.push({ pathname: '/(patient)/reports', params: { symptomText: text, lang } });
  return (
    <ScrollView
      style={{ backgroundColor: colors.pageBg }}
      contentContainerStyle={{ padding: spacing.lg, gap: spacing.lg, paddingBottom: spacing.xxl }}
    >
      <View style={{ gap: 2 }}>
        <Text style={{ fontSize: t.sm, color: colors.textMuted }}>Welcome to</Text>
        <Logo width={120} />
      </View>

      {/* Search entry into the full doctor directory */}
      <Pressable
        onPress={() => router.push('/(patient)/doctors')}
        style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.sm, backgroundColor: colors.surface,
          borderRadius: radii.pill, paddingVertical: 14, paddingHorizontal: spacing.md, ...shadow.card }}
      >
        <Search size={20} color={colors.textMuted} />
        <Text style={{ color: colors.textMuted, fontSize: t.sm }}>Search doctors or specialities</Text>
      </Pressable>

      {/* Symptom triage — the primary path and the screen's focal point */}
      <View style={{ backgroundColor: colors.greenTint, borderRadius: radii.xl, padding: spacing.lg, gap: spacing.sm, ...shadow.card }}>
        <Text style={{ fontSize: t.h3, color: colors.green700, fontWeight: '800' }}>Not sure which doctor?</Text>
        <Text style={{ fontSize: t.sm, color: colors.text }}>
          Describe how you feel — we&apos;ll route you to the right specialist.
        </Text>
        <View style={{ flexDirection: 'row', gap: spacing.sm, marginTop: spacing.xs, marginBottom: spacing.xs }}>
          {(['en', 'hi', 'mr'] as Lang[]).map((l) => (
            <Pressable key={l} onPress={() => setLang(l)}
              style={{ paddingVertical: 6, paddingHorizontal: 16, borderRadius: radii.pill,
                backgroundColor: lang === l ? colors.brightGreen : colors.surface }}>
              <Text style={{ color: lang === l ? colors.white : colors.text, fontSize: t.sm, fontWeight: '600' }}>
                {l.toUpperCase()}
              </Text>
            </Pressable>
          ))}
        </View>
        <Input value={text} onChangeText={setText} multiline placeholder="e.g. chest pain since morning…" />
        <Button title="🎤 Speak instead" variant="ghost" color={colors.green700}
          onPress={() => setTimeout(() => setText(CANNED[lang]), 2000)} />
        <Button title="Find the right doctor" onPress={triage} color={colors.brightGreen}
          disabled={text.trim().length === 0} />
      </View>

      <Text style={{ fontSize: t.h3, color: colors.text, fontWeight: '800' }}>Browse by speciality</Text>
      <SpecialtyGrid onSelect={(s) => router.push({ pathname: '/(patient)/doctors', params: { specialty: s.specialty } })} />
    </ScrollView>
  );
}

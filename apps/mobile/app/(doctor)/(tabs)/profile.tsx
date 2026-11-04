import { useEffect, useRef, useState } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Skeleton } from '@/components/ui/Skeleton';
import { useDoctorProfile } from '@/features/doctor/useDoctorProfile';
import { colors, radii, spacing, type as t } from '@/theme/tokens';

const MAX_KEYWORDS = 15;

export default function ProfileScreen() {
  const { profile, isLoading, save, saving } = useDoctorProfile();
  const [clinic, setClinic] = useState('');
  const [about, setAbout] = useState('');
  const [qualifications, setQualifications] = useState('');
  const [experienceYears, setExperienceYears] = useState('');
  const [keywords, setKeywords] = useState<string[]>([]);
  const [keywordInput, setKeywordInput] = useState('');
  // Seed editable fields from server data once; a refetch on refocus must not
  // discard the doctor's in-progress unsaved edits.
  const loaded = useRef(false);
  useEffect(() => {
    if (profile && !loaded.current) {
      setClinic(profile.clinicAddress);
      setAbout(profile.about);
      setQualifications(profile.qualifications);
      setExperienceYears(String(profile.experienceYears));
      setKeywords(profile.keywords);
      loaded.current = true;
    }
  }, [profile]);
  if (isLoading || !profile) return <View style={{ padding: spacing.lg }}><Skeleton height={200} /></View>;

  const addKeyword = () => {
    const normalized = keywordInput.trim().toLowerCase();
    if (!normalized || keywords.length >= MAX_KEYWORDS || keywords.includes(normalized)) return;
    setKeywords([...keywords, normalized]);
    setKeywordInput('');
  };
  const removeKeyword = (kw: string) => setKeywords(keywords.filter((k) => k !== kw));

  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.h2, fontWeight: '700', color: colors.text }}>{profile.name}</Text>
      <Card>
        <Text style={{ fontSize: t.sm, color: colors.textMuted }}>{profile.specialty} · {profile.qualifications}</Text>
        <Text style={{ fontSize: t.sm, color: colors.text }}>{profile.experienceYears} years experience</Text>
      </Card>
      <Text style={{ fontSize: t.sm, color: colors.textMuted }}>Qualifications</Text>
      <Input value={qualifications} onChangeText={setQualifications} placeholder="MBBS, MD" />
      <Text style={{ fontSize: t.sm, color: colors.textMuted }}>Experience (years)</Text>
      <Input value={experienceYears} onChangeText={setExperienceYears} keyboardType="number-pad" placeholder="5" />
      <Text style={{ fontSize: t.sm, color: colors.textMuted }}>Clinic address</Text>
      <Input value={clinic} onChangeText={setClinic} multiline placeholder="Clinic address" />
      <Text style={{ fontSize: t.sm, color: colors.textMuted }}>About</Text>
      <Input value={about} onChangeText={setAbout} multiline placeholder="About you" />
      <Text style={{ fontSize: t.sm, color: colors.textMuted }}>Keywords ({keywords.length}/{MAX_KEYWORDS})</Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm }}>
        {keywords.map((kw) => (
          <Pressable key={kw} testID="keyword-chip" accessibilityRole="button" onPress={() => removeKeyword(kw)}
            style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.xs, backgroundColor: colors.navyTint,
              borderRadius: radii.pill, paddingVertical: spacing.xs, paddingHorizontal: spacing.sm }}>
            <Text style={{ fontSize: t.sm, color: colors.navy }}>{kw}</Text>
            <Text style={{ fontSize: t.sm, color: colors.navy, fontWeight: '700' }}>×</Text>
          </Pressable>
        ))}
      </View>
      <View style={{ flexDirection: 'row', gap: spacing.sm, alignItems: 'center' }}>
        <View style={{ flex: 1 }}>
          <Input value={keywordInput} onChangeText={setKeywordInput} placeholder="Add a keyword" />
        </View>
        <Pressable testID="add-keyword" accessibilityRole="button" onPress={addKeyword}
          disabled={keywords.length >= MAX_KEYWORDS}
          style={{ height: 48, paddingHorizontal: spacing.md, borderRadius: radii.sm, backgroundColor: colors.navy,
            opacity: keywords.length >= MAX_KEYWORDS ? 0.5 : 1, alignItems: 'center', justifyContent: 'center' }}>
          <Text style={{ color: colors.white, fontSize: t.sm, fontWeight: '600' }}>Add</Text>
        </Pressable>
      </View>
      <Button title="Save profile" color={colors.navy} loading={saving}
        onPress={() => save({
          clinicAddress: clinic, about, qualifications,
          experienceYears: Number(experienceYears) || 0, keywords,
        })} />
    </ScrollView>
  );
}

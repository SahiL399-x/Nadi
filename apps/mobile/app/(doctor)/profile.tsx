import { useEffect, useState } from 'react';
import { ScrollView, Text, View } from 'react-native';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Skeleton } from '@/components/ui/Skeleton';
import { useDoctorProfile } from '@/features/doctor/useDoctorProfile';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function ProfileScreen() {
  const { profile, isLoading, save, saving } = useDoctorProfile();
  const [clinic, setClinic] = useState('');
  const [about, setAbout] = useState('');
  useEffect(() => { if (profile) { setClinic(profile.clinicAddress); setAbout(profile.about); } }, [profile]);
  if (isLoading || !profile) return <View style={{ padding: spacing.lg }}><Skeleton height={200} /></View>;
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.h2, fontWeight: '700', color: colors.text }}>{profile.name}</Text>
      <Card>
        <Text style={{ fontSize: t.sm, color: colors.textMuted }}>{profile.specialty} · {profile.qualifications}</Text>
        <Text style={{ fontSize: t.sm, color: colors.text }}>{profile.experienceYears} years experience</Text>
      </Card>
      <Text style={{ fontSize: t.sm, color: colors.textMuted }}>Clinic address</Text>
      <Input value={clinic} onChangeText={setClinic} multiline placeholder="Clinic address" />
      <Text style={{ fontSize: t.sm, color: colors.textMuted }}>About</Text>
      <Input value={about} onChangeText={setAbout} multiline placeholder="About you" />
      <Button title="Save profile" color={colors.navy} loading={saving}
        onPress={() => save({ clinicAddress: clinic, about })} />
    </ScrollView>
  );
}

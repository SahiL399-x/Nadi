import { Image, Pressable, ScrollView, Text, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Button } from '@/components/ui';
import { CaptureSheet, type Picked } from '@/components/CaptureSheet';
import { useReportUploads } from '@/features/patient/useReportUploads';
import { useTheme } from '@/providers/ThemeProvider';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function Reports() {
  const theme = useTheme();
  const { symptomText, lang } = useLocalSearchParams<{ symptomText: string; lang: string }>();
  const { items, add, remove, retry, allSettled, objectKeys } = useReportUploads();
  const onPicked = (picked: Picked[]) => picked.forEach((p) => add(p.uri, p.kind, p.source));
  const go = () => router.push({ pathname: '/(patient)/analyzing',
    params: { symptomText, lang, keys: JSON.stringify(objectKeys) } });
  return (
    <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }}>
      <Text style={{ fontSize: t.h2, color: theme.primary, fontWeight: '700' }}>Lab reports (optional)</Text>
      <Text style={{ fontSize: t.sm, color: colors.textMuted }}>Scan, choose, or upload any recent reports — or skip.</Text>
      <CaptureSheet onPicked={onPicked} />
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm }}>
        {items.map((it) => (
          <View key={it.id} style={{ width: 96 }}>
            {it.kind === 'image'
              ? <Image source={{ uri: it.uri }} style={{ width: 96, height: 96, borderRadius: 8 }} />
              : <View style={{ width: 96, height: 96, borderRadius: 8, backgroundColor: colors.greenTint, alignItems: 'center', justifyContent: 'center' }}><Text style={{ fontWeight: '800', color: colors.text }}>PDF</Text></View>}
            <Text style={{ fontSize: t.xs, color: it.status === 'error' ? colors.emergency : colors.textMuted }}>
              {it.status === 'uploading' ? 'Uploading…' : it.status === 'done' ? 'Ready' : 'Failed — tap retry'}
            </Text>
            {it.status === 'error' ? <Pressable onPress={() => retry(it.id)}><Text style={{ color: theme.primary }}>Retry</Text></Pressable> : null}
            <Pressable onPress={() => remove(it.id)}><Text style={{ color: colors.textMuted }}>Remove</Text></Pressable>
          </View>
        ))}
      </View>
      <Button title="Continue" onPress={go} color={theme.primary} disabled={!allSettled} />
    </ScrollView>
  );
}

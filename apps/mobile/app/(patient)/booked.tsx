import { Text, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { Button } from '@/components/ui';
import { colors, spacing, type as t } from '@/theme/tokens';

export default function Booked() {
  const { id, slot, name } = useLocalSearchParams<{ id: string; slot: string; name: string }>();
  return (
    <View style={{ flex: 1, justifyContent: 'center', padding: spacing.xl, gap: spacing.md }}>
      <Text style={{ fontSize: t.h1, color: colors.routine, fontWeight: '800' }}>Booked</Text>
      <Text style={{ fontSize: t.body, color: colors.text }}>Your appointment with {name} at {slot} is confirmed.</Text>
      <Button title="Join consultation" onPress={() => router.push({ pathname: '/(patient)/consultation', params: { id: id! } })} />
      <Button title="View prescription" variant="ghost" onPress={() => router.push({ pathname: '/(patient)/prescription', params: { id: id! } })} />
    </View>
  );
}

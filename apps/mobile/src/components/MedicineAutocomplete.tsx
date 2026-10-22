import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { Image } from 'expo-image';
import { Input } from '@/components/ui/Input';
import { useMedicineSearch } from '@/features/doctor/useMedicineSearch';
import { medicineImage } from '@/lib/medicineImage';
import { colors, radii, spacing, type as t } from '@/theme/tokens';

type Props = {
  value: string;
  onChangeText: (v: string) => void;
  onPick: (m: { name: string; strength: string }) => void;
};
export function MedicineAutocomplete({ value, onChangeText, onPick }: Props) {
  const [focused, setFocused] = useState(false);
  const { data } = useMedicineSearch(value);
  const show = focused && (data?.length ?? 0) > 0;
  return (
    <View>
      <Input value={value} placeholder="Drug (search catalog)"
        onChangeText={(v) => { onChangeText(v); setFocused(true); }} />
      {show ? (
        <View style={{ borderWidth: 1, borderColor: colors.border, borderRadius: radii.sm, marginTop: 4 }}>
          {(data ?? []).slice(0, 6).map((m) => (
            <Pressable key={m.id} onPress={() => { onPick({ name: m.name, strength: m.strength }); setFocused(false); }}
              style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.sm, padding: spacing.sm,
                borderBottomWidth: 1, borderBottomColor: colors.border }}>
              <Image source={{ uri: medicineImage(m.name) }} style={{ width: 34, height: 34, borderRadius: radii.sm, backgroundColor: colors.lightGrey }} contentFit="cover" />
              <Text style={{ fontSize: t.sm, color: colors.text, flex: 1 }}>{m.name} {m.strength} · {m.form}</Text>
            </Pressable>
          ))}
        </View>
      ) : null}
    </View>
  );
}

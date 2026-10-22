import { Pressable, Text, View } from 'react-native';
import { router } from 'expo-router';
import { Bell as BellIcon } from 'lucide-react-native';
import { useNotifications } from '@/store/notifications';
import { colors } from '@/theme/tokens';

export function Bell({ color = colors.text }: { color?: string }) {
  const count = useNotifications((s) => s.items.length);
  return (
    <Pressable onPress={() => router.push('/notifications')} hitSlop={8}>
      <BellIcon size={24} color={color} />
      {count > 0 ? (
        <View style={{ position: 'absolute', top: -5, right: -5, minWidth: 16, height: 16, borderRadius: 8,
          backgroundColor: colors.emergency, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 3 }}>
          <Text style={{ color: colors.white, fontSize: 10, fontWeight: '800' }}>{count > 9 ? '9+' : count}</Text>
        </View>
      ) : null}
    </Pressable>
  );
}

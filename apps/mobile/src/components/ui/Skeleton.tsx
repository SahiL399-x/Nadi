import { useEffect } from 'react';
import Animated, { useAnimatedStyle, useSharedValue, withRepeat, withTiming } from 'react-native-reanimated';
import { colors, radii } from '@/theme/tokens';
export function Skeleton({ height = 16, width = '100%' as number | `${number}%` }) {
  const o = useSharedValue(0.4);
  useEffect(() => { o.value = withRepeat(withTiming(1, { duration: 800 }), -1, true); }, [o]);
  const style = useAnimatedStyle(() => ({ opacity: o.value }));
  return <Animated.View style={[{ height, width, backgroundColor: colors.border, borderRadius: radii.sm }, style]} />;
}

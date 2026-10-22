import { Image } from 'expo-image';

// The Nadi wordmark (leaf + pulse). Transparent PNG, wide aspect inside a square.
export function Logo({ width = 200 }: { width?: number }) {
  return (
    <Image
      source={require('../../assets/logo.png')}
      style={{ width, height: width * 0.56 }}
      contentFit="contain"
      transition={200}
    />
  );
}

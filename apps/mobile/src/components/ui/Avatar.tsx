import { Image } from 'expo-image';
export function Avatar({ uri, size = 56 }: { uri: string; size?: number }) {
  return <Image source={{ uri }} style={{ width: size, height: size, borderRadius: size / 2 }}
    contentFit="cover" transition={150} cachePolicy="disk" />;
}

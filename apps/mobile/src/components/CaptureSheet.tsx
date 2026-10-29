import { Pressable, Text, View } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import * as DocumentPicker from 'expo-document-picker';
import DocumentScanner from 'react-native-document-scanner-plugin';
import { classifyPicked } from '@/features/patient/capture';
import { colors, radii, spacing, type as t } from '@/theme/tokens';

export type Picked = { uri: string; kind: 'image' | 'pdf'; source: 'scan' | 'upload' };

export function CaptureSheet({ onPicked }: { onPicked: (items: Picked[]) => void }) {
  const scan = async () => {
    const { scannedImages } = await DocumentScanner.scanDocument({ maxNumDocuments: 10 });
    if (scannedImages?.length) onPicked(scannedImages.map((uri: string) => ({ uri, kind: 'image' as const, source: 'scan' as const })));
  };
  const gallery = async () => {
    const res = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images, allowsMultipleSelection: true, quality: 1,
    });
    if (!res.canceled) onPicked(res.assets.map((a) => ({ uri: a.uri, kind: 'image', source: 'upload' })));
  };
  const file = async () => {
    const res = await DocumentPicker.getDocumentAsync({ type: ['application/pdf', 'image/*'], multiple: true });
    if (!res.canceled) onPicked(res.assets.map((a) => ({
      uri: a.uri, kind: classifyPicked(a.name, a.mimeType), source: 'upload',
    })));
  };
  const Item = ({ label, onPress }: { label: string; onPress: () => void }) => (
    <Pressable onPress={onPress} style={{ paddingVertical: spacing.md, paddingHorizontal: spacing.lg,
      backgroundColor: colors.surface, borderRadius: radii.lg, borderWidth: 1, borderColor: colors.border }}>
      <Text style={{ fontSize: t.body, fontWeight: '700', color: colors.text }}>{label}</Text>
    </Pressable>
  );
  return (
    <View style={{ gap: spacing.sm }}>
      <Item label="Scan with camera" onPress={scan} />
      <Item label="Choose from gallery" onPress={gallery} />
      <Item label="Upload a file (PDF/image)" onPress={file} />
    </View>
  );
}

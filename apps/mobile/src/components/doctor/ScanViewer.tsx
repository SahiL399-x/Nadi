import { Image, Modal, Pressable, ScrollView, useWindowDimensions } from 'react-native';

export function ScanViewer({ uri, visible, onClose }: { uri: string; visible: boolean; onClose: () => void }) {
  const { width, height } = useWindowDimensions();
  return (
    <Modal visible={visible} onRequestClose={onClose} animationType="fade">
      <Pressable onPress={onClose} style={{ flex: 1, backgroundColor: '#000' }}>
        <ScrollView maximumZoomScale={4} minimumZoomScale={1} centerContent
          contentContainerStyle={{ width, height, alignItems: 'center', justifyContent: 'center' }}>
          <Image source={{ uri }} style={{ width, height }} resizeMode="contain" />
        </ScrollView>
      </Pressable>
    </Modal>
  );
}

import { Text, View } from 'react-native';
import { useTheme } from '@/providers/ThemeProvider';
export default function Home() {
  const theme = useTheme();
  return <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
    <Text style={{ color: theme.primary, fontSize: 24, fontWeight: '700' }}>Portal</Text>
  </View>;
}

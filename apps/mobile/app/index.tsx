import { useEffect, useState } from 'react';
import { ActivityIndicator, View } from 'react-native';
import { Redirect } from 'expo-router';
import { useSession } from '@/store/session';

export default function Index() {
  const role = useSession((s) => s.role);
  const restore = useSession((s) => s.restoreSession);
  const [ready, setReady] = useState(false);
  useEffect(() => { restore().finally(() => setReady(true)); }, [restore]);
  if (!ready) return <View style={{ flex: 1, justifyContent: 'center' }}><ActivityIndicator /></View>;
  if (role === 'patient') return <Redirect href="/(patient)" />;
  if (role === 'doctor') return <Redirect href="/(doctor)" />;
  if (role === 'pharmacy') return <Redirect href="/(pharmacy)" />;
  return <Redirect href="/(auth)/phone" />;
}

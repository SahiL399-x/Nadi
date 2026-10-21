import { useEffect, useState } from 'react';
import { Text, View } from 'react-native';
import * as Network from 'expo-network';

export function ConnectivityBanner() {
  const [online, setOnline] = useState(true);
  useEffect(() => {
    let active = true;
    const check = async () => {
      const state = await Network.getNetworkStateAsync();
      if (active) setOnline(Boolean(state.isInternetReachable ?? state.isConnected));
    };
    check();
    const id = setInterval(check, 5000);
    return () => { active = false; clearInterval(id); };
  }, []);
  if (online) return null;
  return (
    <View className="bg-red-700 px-4 py-2">
      <Text className="text-white text-center" style={{ fontSize: 15 }}>No connection — check Wi-Fi</Text>
    </View>
  );
}

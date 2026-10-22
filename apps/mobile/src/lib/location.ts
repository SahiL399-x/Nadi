import { useLocation } from '@/store/location';

// Request location permission and update the store with the device GPS fix.
// Defensive: expo-location is a native module absent from builds made before it
// was added, so a missing module (or a denied permission) just keeps the default.
export async function requestLocation(): Promise<void> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const Location = require('expo-location');
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== 'granted') return;
    const pos = await Location.getCurrentPositionAsync({ accuracy: 3 });
    useLocation.getState().setLocation(pos.coords.latitude, pos.coords.longitude);
  } catch {
    /* module missing or permission unavailable — keep the default centre */
  }
}

import { Camera, Map, Marker } from '@maplibre/maplibre-react-native';
import { Image } from 'expo-image';
import { Text, View } from 'react-native';
import type { Doctor } from '@/api/schemas';
import { useLocation } from '@/store/location';
import { placeNear } from '@/lib/geo';
import { colors, shadow } from '@/theme/tokens';

// free, no key, no billing — https://openfreemap.org
const STYLE_URL = 'https://tiles.openfreemap.org/styles/liberty';

export function DoctorsMap({ doctors }: { doctors: Doctor[] }) {
  const { lat, lng } = useLocation();
  return (
    <Map style={{ flex: 1 }} mapStyle={STYLE_URL}>
      <Camera initialViewState={{ center: [lng, lat], zoom: 12.5 }} />
      {doctors.map((d, i) => {
        const p = placeNear(lat, lng, i);
        return (
          <Marker key={d.id} id={d.id} testID={`doctor-marker-${d.id}`} lngLat={[p.lng, p.lat]}>
            <View style={{ alignItems: 'center' }}>
              <View style={{ width: 46, height: 46, borderRadius: 23, borderWidth: 3, borderColor: colors.brightGreen,
                overflow: 'hidden', backgroundColor: colors.greenTint }}>
                <Image source={d.photoUrl ? { uri: d.photoUrl } : undefined} style={{ width: '100%', height: '100%' }} contentFit="cover" />
              </View>
              <View style={{ marginTop: 2, flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: colors.white,
                borderRadius: 8, paddingHorizontal: 6, paddingVertical: 2, ...shadow.card }}>
                <Text style={{ fontSize: 10, fontWeight: '800', color: colors.text }}>₹{d.feeInr}</Text>
                <Text style={{ fontSize: 10, fontWeight: '700', color: colors.green700 }}>★{d.rating}</Text>
              </View>
            </View>
          </Marker>
        );
      })}
    </Map>
  );
}

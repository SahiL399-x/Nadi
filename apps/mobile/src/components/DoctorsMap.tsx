import { Camera, Map, Marker } from '@maplibre/maplibre-react-native';
import { View, Text } from 'react-native';
import type { Doctor } from '@/api/schemas';
import { patientLocation } from '@/api/patient';
import { colors } from '@/theme/tokens';

// free, no key, no billing — https://openfreemap.org
const STYLE_URL = 'https://tiles.openfreemap.org/styles/liberty';

export function DoctorsMap({ doctors }: { doctors: Doctor[] }) {
  return (
    <Map style={{ flex: 1 }} mapStyle={STYLE_URL}>
      <Camera
        initialViewState={{ center: [patientLocation.lng, patientLocation.lat], zoom: 11 }}
      />
      {doctors.map((d) => (
        <Marker key={d.id} id={d.id} testID={`doctor-marker-${d.id}`} lngLat={[d.lng, d.lat]}>
          <View style={{ backgroundColor: colors.navy, borderRadius: 999, paddingHorizontal: 8, paddingVertical: 4 }}>
            <Text style={{ color: '#fff', fontSize: 11 }}>₹{d.feeInr}</Text>
          </View>
        </Marker>
      ))}
    </Map>
  );
}

const KM_PER_DEG = 111; // ~111 km per degree of latitude

// Deterministically scatter the i-th doctor/pharmacy in rings around a centre so
// results always appear near the patient's current location on the map (demo).
export function placeNear(centerLat: number, centerLng: number, i: number) {
  const golden = 2.399963; // golden angle (rad) → even angular spread
  const angle = i * golden;
  const radiusKm = 0.6 + (i % 6) * 0.8; // 0.6–4.6 km
  const dLat = (radiusKm * Math.cos(angle)) / KM_PER_DEG;
  const dLng = (radiusKm * Math.sin(angle)) / (KM_PER_DEG * Math.cos((centerLat * Math.PI) / 180));
  return {
    lat: centerLat + dLat,
    lng: centerLng + dLng,
    distanceKm: Math.round(radiusKm * 10) / 10,
  };
}

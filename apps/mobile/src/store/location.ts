import { create } from 'zustand';

// Patient's map centre. Defaults to Nashik; replaced by real GPS at login when
// expo-location is available (see src/lib/location.ts).
type LocationState = {
  lat: number;
  lng: number;
  setLocation: (lat: number, lng: number) => void;
};

export const useLocation = create<LocationState>((set) => ({
  lat: 19.9975,
  lng: 73.7898,
  setLocation: (lat, lng) => set({ lat, lng }),
}));

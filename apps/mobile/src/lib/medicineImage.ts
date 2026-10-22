// Curated royalty-free medicine/pill photos (Unsplash). Picked deterministically
// by name so a given drug always shows the same thumbnail (demo).
const IMAGES = [
  'https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=120&h=120&fit=crop',
  'https://images.unsplash.com/photo-1587854692152-cbe660dbde88?w=120&h=120&fit=crop',
  'https://images.unsplash.com/photo-1631549916768-4119b2e5f926?w=120&h=120&fit=crop',
  'https://images.unsplash.com/photo-1550572017-edd951aa8ca6?w=120&h=120&fit=crop',
  'https://images.unsplash.com/photo-1471864190281-a93a3070b6de?w=120&h=120&fit=crop',
  'https://images.unsplash.com/photo-1585435557343-3b092031a831?w=120&h=120&fit=crop',
];

export function medicineImage(name: string): string {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
  return IMAGES[h % IMAGES.length] as string;
}

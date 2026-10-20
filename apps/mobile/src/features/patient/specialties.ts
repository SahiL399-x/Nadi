import type { ComponentType } from 'react';
import { Stethoscope, Baby, HeartPulse, Ear, Bone, Eye, Droplet, User } from 'lucide-react-native';

export type Specialty = { label: string; specialty: string; Icon: ComponentType<{ size?: number; color?: string }> };

export const SPECIALTIES: Specialty[] = [
  { label: 'General Physician', specialty: 'General Physician', Icon: Stethoscope },
  { label: "Women's Health", specialty: 'Gynaecology', Icon: User },
  { label: 'Skin Specialist', specialty: 'Dermatology', Icon: Droplet },
  { label: 'Child Care', specialty: 'Paediatrics', Icon: Baby },
  { label: 'Heart', specialty: 'Cardiology', Icon: HeartPulse },
  { label: 'Bone & Joint', specialty: 'Orthopaedics', Icon: Bone },
  { label: 'Ear, Nose & Throat', specialty: 'ENT', Icon: Ear },
  { label: 'Eye Specialist', specialty: 'General Physician', Icon: Eye },
];

export type Acuity = 'ROUTINE' | 'PRIORITY' | 'URGENT' | 'EMERGENCY';

export interface LabValue {
  analyte: string; value: number; unit: string; refRange: string; flag: 'L' | 'N' | 'H';
}
export interface TriageInput {
  symptomText: string; reportImageUris: string[]; age?: number;
  sex?: 'M' | 'F' | 'O'; lang: 'en' | 'hi' | 'mr';
}
export interface TriageResult {
  acuity: Acuity; acuityConfidence: number;
  specialties: { name: string; score: number }[];
  drivers: { feature: string; contribution: number }[];
  labs: LabValue[]; redFlags: string[]; modelVersion: string;
}
export interface Doctor {
  id: string; name: string; specialty: string; qualifications: string;
  experienceYears: number; distanceKm: number; feeInr: number; rating: number;
  reviewCount: number; languages: string[]; nextSlot: string;
  photoUrl: string; availableSlots: string[];
}
export interface QueueItem {
  id: string; patientName: string; patientAge: number; patientSex: 'M' | 'F' | 'O';
  acuity: Acuity; complaint: string; bookedFor: string; triage: TriageResult;
}
export interface PrescriptionLine {
  drug: string; strength: string; frequency: string; durationDays: number; notes?: string;
}
export interface Prescription {
  id: string; patientName: string; doctorName: string; issuedAt: string;
  lines: PrescriptionLine[]; status: 'PENDING' | 'ACCEPTED' | 'DECLINED' | 'DELIVERED';
}
export interface Pharmacy {
  id: string; name: string; distanceKm: number; deliversInMins: number; isOpen: boolean;
}

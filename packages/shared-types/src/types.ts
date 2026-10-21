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
  experienceYears: number; distanceKm: number; lat: number; lng: number; feeInr: number; rating: number;
  reviewCount: number; languages: string[]; nextSlot: string;
  photoUrl: string; availableSlots: string[];
}
export interface QueueItem {
  id: string; patientId: string; patientName: string; patientAge: number; patientSex: 'M' | 'F' | 'O';
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

// --- v2 contract: doctor & pharmacy portals (backend expansion, ADR-0005) ---

export type AppointmentStatus = 'Upcoming' | 'Arrived' | 'In Progress' | 'Completed';

export interface Appointment {
  id: string; patientId: string; patientName: string; patientAge: number; patientSex: 'M' | 'F' | 'O';
  photoUrl: string; time: string; status: AppointmentStatus;
  acuity: Acuity | null; complaint: string;
}
export interface Medicine { id: string; name: string; strength: string; form: string; }
export interface DoctorStats {
  appointmentsToday: number; pending: number; completed: number;
  prescriptionsIssued: number; newPatients: number;
}
export interface PharmacyStats {
  newOrders: number; inProgress: number; outForDelivery: number; completedToday: number;
}
export type OrderStatus =
  | 'TO_VERIFY' | 'PENDING' | 'PREPARING' | 'VERIFIED' | 'OUT_FOR_DELIVERY'
  | 'DELIVERED' | 'COMPLETED' | 'CANCELLED' | 'ACCEPTED' | 'DECLINED';
export interface Order {
  id: string; orderNo: string; patientName: string; phone: string;
  itemsCount: number; totalInr: number; status: OrderStatus; placedAt: string;
}
export interface Visit { visitedAt: string; summary: string; status: string; }
export interface PatientProfile {
  name: string; age: number; sex: string;
  conditions: string[]; allergies: string[]; familyHistory: string[];
  noKnownAllergies: boolean; latestVisit: Visit | null; visits: Visit[]; prescriptions: string[];
}
export interface DoctorPrescriptionListItem {
  id: string; patientName: string; issuedAt: string; firstDrug: string; status: string;
}
export interface LabReport { id: string; patientName: string; date: string; status: string; }
export interface Availability { weekday: number; morning: string; evening: string; isOpen: boolean; }
export interface DoctorProfile {
  name: string; specialty: string; qualifications: string; experienceYears: number;
  clinicAddress: string; about: string; photoUrl: string;
}
export interface ConsultationNote { id: string; text: string; createdAt: string; }

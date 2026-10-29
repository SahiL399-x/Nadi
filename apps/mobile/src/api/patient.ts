import { z } from 'zod';
import { api } from '@/api/client';
import { useLocation } from '@/store/location';
import {
  DoctorSchema, TriageResponseSchema, IntakeResultSchema, ConsultationDetailSchema,
  PrescriptionSchema, PharmacySchema, type Doctor, type Pharmacy, type Prescription,
} from '@/api/schemas';

const here = () => useLocation.getState();

export type IntakeInput = {
  symptomText: string; reportImageUris: string[];
  age?: number; sex?: 'M' | 'F' | 'O'; lang: 'en' | 'hi' | 'mr';
};

export const intake = (input: IntakeInput) =>
  api.post('/v1/consultations/intake', input, IntakeResultSchema);

// Direct-browse booking has no prior triage/consultation. Return the existing id if the
// patient came via triage, else create one on-demand via a minimal intake so the booking
// still produces a consultation the doctor sees in their queue.
export const ensureConsultation = async (existingId: string | undefined, specialtyHint: string): Promise<string> => {
  if (existingId) return existingId;
  const r = await intake({ symptomText: `Direct booking: ${specialtyHint}`, reportImageUris: [], lang: 'en' });
  return r.consultationId;
};

export const getTriage = (id: string) =>
  api.get(`/v1/consultations/${id}/triage`, TriageResponseSchema);

export const getConsultation = (id: string) =>
  api.get(`/v1/consultations/${id}`, ConsultationDetailSchema);

export const searchDoctors = (p: { specialty?: string; lang?: string }): Promise<Doctor[]> => {
  const { lat, lng } = here();
  const q = new URLSearchParams({ lat: String(lat), lng: String(lng), radiusKm: '50' });
  if (p.specialty) q.set('specialty', p.specialty);
  if (p.lang) q.set('lang', p.lang);
  return api.get(`/v1/doctors?${q.toString()}`, z.array(DoctorSchema));
};

export const getDoctor = (id: string) => api.get(`/v1/doctors/${id}`, DoctorSchema);

export const book = (id: string, body: { doctorId: string; slot: string }) =>
  api.post(`/v1/consultations/${id}/book`, body, z.object({ booked: z.boolean() }));

export const getPrescription = (id: string): Promise<Prescription> =>
  api.get(`/v1/prescriptions/${id}`, PrescriptionSchema);

export const listPharmacies = (): Promise<Pharmacy[]> => {
  const { lat, lng } = here();
  const q = new URLSearchParams({ lat: String(lat), lng: String(lng), radiusKm: '50' });
  return api.get(`/v1/pharmacies?${q.toString()}`, z.array(PharmacySchema));
};

export const consent = (prescriptionId: string, pharmacyIds: string[]) =>
  api.post(`/v1/prescriptions/${prescriptionId}/consent`, { pharmacyIds },
    z.object({ consented: z.boolean(), routedTo: z.string() }));

export const signUpload = (body?: { source?: 'scan' | 'upload'; ext?: 'webp' | 'pdf' | 'jpg' | 'png' }) =>
  api.post('/v1/uploads/sign', body ?? {}, z.object({ url: z.string(), objectKey: z.string() }));

export const patientLocation = () => here();

import { z } from 'zod';
import { api } from '@/api/client';
import { AcuitySchema } from '@/api/schemas';

export const DoctorStatsSchema = z.object({
  appointmentsToday: z.number(), pending: z.number(), completed: z.number(),
  prescriptionsIssued: z.number(), newPatients: z.number(),
});
export const AppointmentSchema = z.object({
  id: z.string(), patientId: z.string(), patientName: z.string(), patientAge: z.number(),
  patientSex: z.string(), photoUrl: z.string(), time: z.string(), status: z.string(),
  acuity: AcuitySchema.nullable(), complaint: z.string(),
});
export const MedicineSchema = z.object({
  id: z.string(), name: z.string(), strength: z.string(), form: z.string(),
});
export const VisitSchema = z.object({ visitedAt: z.string(), summary: z.string(), status: z.string() });
export const PatientProfileSchema = z.object({
  name: z.string(), age: z.number(), sex: z.string(),
  conditions: z.array(z.string()), allergies: z.array(z.string()), familyHistory: z.array(z.string()),
  noKnownAllergies: z.boolean(), latestVisit: VisitSchema.nullable(),
  visits: z.array(VisitSchema), prescriptions: z.array(z.string()),
});
export const DoctorPrescriptionSchema = z.object({
  id: z.string(), patientName: z.string(), issuedAt: z.string(), firstDrug: z.string(), status: z.string(),
});
export const LabReportSchema = z.object({
  id: z.string(), patientName: z.string(), date: z.string(), status: z.string(),
});
export const AvailabilitySchema = z.object({
  weekday: z.number(), morning: z.string(), evening: z.string(), isOpen: z.boolean(),
});
export const DoctorProfileSchema = z.object({
  name: z.string(), specialty: z.string(), qualifications: z.string(), experienceYears: z.number(),
  clinicAddress: z.string(), about: z.string(), photoUrl: z.string(),
});
export const NoteSchema = z.object({ id: z.string(), text: z.string(), createdAt: z.string() });

export type DoctorStats = z.infer<typeof DoctorStatsSchema>;
export type Appointment = z.infer<typeof AppointmentSchema>;
export type Medicine = z.infer<typeof MedicineSchema>;
export type PatientProfile = z.infer<typeof PatientProfileSchema>;
export type DoctorPrescription = z.infer<typeof DoctorPrescriptionSchema>;
export type LabReport = z.infer<typeof LabReportSchema>;
export type Availability = z.infer<typeof AvailabilitySchema>;
export type DoctorProfile = z.infer<typeof DoctorProfileSchema>;
export type Note = z.infer<typeof NoteSchema>;

export const getDoctorStats = () => api.get('/v1/doctor/stats', DoctorStatsSchema);

export const getAppointments = (date?: string): Promise<Appointment[]> => {
  const q = date ? `?date=${encodeURIComponent(date)}` : '';
  return api.get(`/v1/doctor/appointments${q}`, z.array(AppointmentSchema));
};

export const searchMedicines = (q?: string): Promise<Medicine[]> => {
  const query = q && q.trim() ? `?q=${encodeURIComponent(q.trim())}` : '';
  return api.get(`/v1/medicines${query}`, z.array(MedicineSchema));
};

export const getPatient = (patientId: string) =>
  api.get(`/v1/doctor/patients/${patientId}`, PatientProfileSchema);

export const listDoctorPrescriptions = (status: 'all' | 'active' | 'completed' = 'all') =>
  api.get(`/v1/doctor/prescriptions?status=${status}`, z.array(DoctorPrescriptionSchema));

export const listLabReports = (status: 'all' | 'pending' | 'completed' = 'all') =>
  api.get(`/v1/doctor/lab-reports?status=${status}`, z.array(LabReportSchema));

export const getAvailability = () => api.get('/v1/doctor/availability', z.array(AvailabilitySchema));

export const putAvailability = (days: Availability[]) =>
  api.put('/v1/doctor/availability', { days }, z.array(AvailabilitySchema));

export const getDoctorProfile = () => api.get('/v1/doctor/profile', DoctorProfileSchema);

export const updateDoctorProfile = (body: { clinicAddress?: string; about?: string }) =>
  api.put('/v1/doctor/profile', body, DoctorProfileSchema);

export const addNote = (consultationId: string, text: string) =>
  api.post(`/v1/consultations/${consultationId}/notes`, { text }, z.object({ id: z.string() }));

export const listNotes = (consultationId: string) =>
  api.get(`/v1/consultations/${consultationId}/notes`, z.array(NoteSchema));

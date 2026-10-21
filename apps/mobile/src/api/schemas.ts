import { z } from 'zod';

export const AcuitySchema = z.enum(['ROUTINE', 'PRIORITY', 'URGENT', 'EMERGENCY']);

export const TokenPairSchema = z.object({
  accessToken: z.string(), refreshToken: z.string(),
  role: z.enum(['patient', 'doctor', 'pharmacy']), userId: z.string(),
});

export const LabValueSchema = z.object({
  analyte: z.string(), value: z.number(), unit: z.string(),
  refRange: z.string(), flag: z.enum(['L', 'N', 'H']),
});

export const TriageResultSchema = z.object({
  acuity: AcuitySchema, acuityConfidence: z.number(),
  specialties: z.array(z.object({ name: z.string(), score: z.number() })),
  drivers: z.array(z.object({ feature: z.string(), contribution: z.number() })),
  labs: z.array(LabValueSchema), redFlags: z.array(z.string()), modelVersion: z.string(),
});
export const TriagePendingSchema = z.object({ status: z.literal('pending') });
export const TriageResponseSchema = z.union([TriagePendingSchema, TriageResultSchema]);

export const DoctorSchema = z.object({
  id: z.string(), name: z.string(), specialty: z.string(), qualifications: z.string(),
  experienceYears: z.number(), distanceKm: z.number(), lat: z.number(), lng: z.number(),
  feeInr: z.number(), rating: z.number(), reviewCount: z.number(),
  languages: z.array(z.string()), nextSlot: z.string(),
  photoUrl: z.string(), availableSlots: z.array(z.string()),
});

export const QueueItemSchema = z.object({
  id: z.string(), patientId: z.string(), patientName: z.string(), patientAge: z.number(),
  patientSex: z.enum(['M', 'F', 'O']), acuity: AcuitySchema, complaint: z.string(),
  bookedFor: z.string(), triage: TriageResultSchema,
});

export const PrescriptionLineSchema = z.object({
  drug: z.string(), strength: z.string(), frequency: z.string(),
  durationDays: z.number(), notes: z.string().nullish(), // backend sends null, not omitted
});
export const PrescriptionSchema = z.object({
  id: z.string(), patientName: z.string(), doctorName: z.string(), issuedAt: z.string(),
  lines: z.array(PrescriptionLineSchema),
  status: z.enum(['PENDING', 'ACCEPTED', 'DECLINED', 'DELIVERED']),
});
export const OfferSchema = z.object({
  id: z.string(), prescriptionId: z.string(), patientName: z.string(),
  status: z.enum(['PENDING', 'ACCEPTED', 'DECLINED']), lines: z.array(PrescriptionLineSchema),
});

export const ConsultationDetailSchema = z.object({
  id: z.string(),
  status: z.enum(['PENDING', 'TRIAGED', 'BOOKED', 'IN_PROGRESS', 'DONE']),
  doctorId: z.string().nullish(),
  bookedFor: z.string().nullish(),
  prescriptionId: z.string().nullish(),
});

export const PharmacySchema = z.object({
  id: z.string(), name: z.string(), distanceKm: z.number(),
  deliversInMins: z.number(), isOpen: z.boolean(),
});
export const IntakeResultSchema = z.object({ consultationId: z.string(), jobId: z.string() });

export type TokenPair = z.infer<typeof TokenPairSchema>;
export type TriageResult = z.infer<typeof TriageResultSchema>;
export type Doctor = z.infer<typeof DoctorSchema>;
export type QueueItem = z.infer<typeof QueueItemSchema>;
export type Prescription = z.infer<typeof PrescriptionSchema>;
export type Offer = z.infer<typeof OfferSchema>;
export type IntakeResult = z.infer<typeof IntakeResultSchema>;
export type ConsultationDetail = z.infer<typeof ConsultationDetailSchema>;
export type Pharmacy = z.infer<typeof PharmacySchema>;

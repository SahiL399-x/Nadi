import { z } from 'zod';
import { api } from '@/api/client';

export const MyAppointmentSchema = z.object({
  consultationId: z.string(), doctorName: z.string(), specialty: z.string(),
  status: z.string(), slot: z.string(),
});
export const MyPrescriptionSchema = z.object({
  id: z.string(), doctorName: z.string(), status: z.string(), items: z.number(),
});
export const MyReportSchema = z.object({ id: z.string(), objectKey: z.string() });

export type MyAppointment = z.infer<typeof MyAppointmentSchema>;
export type MyPrescription = z.infer<typeof MyPrescriptionSchema>;
export type MyReport = z.infer<typeof MyReportSchema>;

export const getMyAppointments = () => api.get('/v1/me/appointments', z.array(MyAppointmentSchema));
export const getMyPrescriptions = () => api.get('/v1/me/prescriptions', z.array(MyPrescriptionSchema));
export const getMyReports = () => api.get('/v1/me/reports', z.array(MyReportSchema));

import { z } from 'zod';
import { api } from '@/api/client';
import { QueueItemSchema, type QueueItem } from '@/api/schemas';

export type PrescriptionLineInput = {
  drug: string; strength: string; frequency: string; durationDays: number; notes?: string;
};

export const getQueue = (): Promise<QueueItem[]> =>
  api.get('/v1/doctor/queue', z.array(QueueItemSchema));

export const prescribe = (consultationId: string, lines: PrescriptionLineInput[]) =>
  api.post(`/v1/doctor/consultations/${consultationId}/prescribe`, { lines },
    z.object({ prescriptionId: z.string() }));

export const refer = (consultationId: string, body: { toSpecialty: string; reason: string }) =>
  api.post(`/v1/doctor/consultations/${consultationId}/refer`, body,
    z.object({ referred: z.boolean() }));

import { z } from 'zod';
import { api } from '@/api/client';
import { OfferSchema, type Offer } from '@/api/schemas';

export const getInbox = (): Promise<Offer[]> =>
  api.get('/v1/pharmacy/inbox', z.array(OfferSchema));

export const acceptOffer = (id: string) =>
  api.post(`/v1/pharmacy/offers/${id}/accept`, {}, z.object({ accepted: z.boolean() }));

export const declineOffer = (id: string) =>
  api.post(`/v1/pharmacy/offers/${id}/decline`, {}, z.object({ declined: z.boolean(), forwarded: z.boolean() }));

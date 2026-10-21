import { z } from 'zod';
import { api } from '@/api/client';

export const PharmacyStatsSchema = z.object({
  newOrders: z.number(), inProgress: z.number(), outForDelivery: z.number(), completedToday: z.number(),
});
export const OrderSchema = z.object({
  id: z.string(), orderNo: z.string(), patientName: z.string(), phone: z.string(),
  itemsCount: z.number(), totalInr: z.number(), status: z.string(), placedAt: z.string(),
});

export type PharmacyStats = z.infer<typeof PharmacyStatsSchema>;
export type Order = z.infer<typeof OrderSchema>;
export type OrderStatusFilter =
  | 'all' | 'pending' | 'accepted' | 'to_verify' | 'verified' | 'preparing'
  | 'out_for_delivery' | 'delivered' | 'completed' | 'cancelled' | 'declined';

// Mirrors apps/api/app/services/pharmacy_service.py `_ALLOWED` exactly (same keys + order).
export const ALLOWED_TRANSITIONS: Record<string, string[]> = {
  PENDING: ['TO_VERIFY', 'VERIFIED', 'PREPARING', 'CANCELLED'],
  TO_VERIFY: ['VERIFIED', 'PREPARING', 'CANCELLED'],
  VERIFIED: ['PREPARING', 'CANCELLED'],
  PREPARING: ['OUT_FOR_DELIVERY', 'CANCELLED'],
  OUT_FOR_DELIVERY: ['DELIVERED', 'CANCELLED'],
  DELIVERED: ['COMPLETED'],
  COMPLETED: [],
  CANCELLED: [],
  DECLINED: [],
  ACCEPTED: ['PREPARING', 'CANCELLED'],
};
export const nextStatuses = (current: string): string[] => ALLOWED_TRANSITIONS[current] ?? [];

export const STATUS_LABEL: Record<string, string> = {
  PENDING: 'New', ACCEPTED: 'Accepted', TO_VERIFY: 'To verify', VERIFIED: 'Verified',
  PREPARING: 'Preparing', OUT_FOR_DELIVERY: 'Out for delivery', DELIVERED: 'Delivered',
  COMPLETED: 'Completed', CANCELLED: 'Cancelled', DECLINED: 'Declined',
};

export const getPharmacyStats = () => api.get('/v1/pharmacy/stats', PharmacyStatsSchema);

export const getOrders = (status: OrderStatusFilter = 'all'): Promise<Order[]> =>
  api.get(`/v1/pharmacy/orders?status=${status}`, z.array(OrderSchema));

export const setOrderStatus = (offerId: string, status: string) =>
  api.post(`/v1/pharmacy/orders/${offerId}/status`, { status }, z.object({ status: z.string() }));

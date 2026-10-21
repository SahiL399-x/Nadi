import { useQuery } from '@tanstack/react-query';
import { getOrders, type OrderStatusFilter } from '@/api/pharmacyPortal';
import { pollInterval } from '@/lib/polling';

export function useOrders(status: OrderStatusFilter) {
  return useQuery({
    queryKey: ['orders', status],
    queryFn: () => getOrders(status),
    refetchInterval: () => pollInterval(true, 5000),
  });
}

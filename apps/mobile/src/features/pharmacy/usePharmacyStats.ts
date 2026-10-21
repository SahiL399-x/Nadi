import { useQuery } from '@tanstack/react-query';
import { getPharmacyStats } from '@/api/pharmacyPortal';
import { pollInterval } from '@/lib/polling';

export function usePharmacyStats() {
  return useQuery({
    queryKey: ['pharmacyStats'],
    queryFn: getPharmacyStats,
    refetchInterval: () => pollInterval(true, 8000),
  });
}

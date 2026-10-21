import { useQuery } from '@tanstack/react-query';
import { getDoctorStats } from '@/api/doctorPortal';
import { pollInterval } from '@/lib/polling';

export function useDoctorStats() {
  return useQuery({
    queryKey: ['doctorStats'],
    queryFn: getDoctorStats,
    refetchInterval: () => pollInterval(true, 10000),
  });
}

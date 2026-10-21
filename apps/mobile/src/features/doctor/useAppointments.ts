import { useQuery } from '@tanstack/react-query';
import { getAppointments } from '@/api/doctorPortal';
import { pollInterval } from '@/lib/polling';

export function useAppointments(dateIso: string) {
  return useQuery({
    queryKey: ['appointments', dateIso],
    queryFn: () => getAppointments(dateIso),
    refetchInterval: () => pollInterval(true, 5000),
  });
}

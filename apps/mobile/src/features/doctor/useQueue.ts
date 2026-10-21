import { useQuery } from '@tanstack/react-query';
import { getQueue } from '@/api/doctor';
import { pollInterval } from '@/lib/polling';

export function useQueue() {
  return useQuery({ queryKey: ['queue'], queryFn: getQueue, refetchInterval: () => pollInterval(true, 4000) });
}

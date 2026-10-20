import { useQuery } from '@tanstack/react-query';
import { getInbox } from '@/api/pharmacy';
import { pollInterval } from '@/lib/polling';

export function useInbox() {
  return useQuery({ queryKey: ['inbox'], queryFn: getInbox, refetchInterval: () => pollInterval(true, 4000) });
}

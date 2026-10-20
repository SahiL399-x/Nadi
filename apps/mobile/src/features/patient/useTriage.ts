import { useQuery } from '@tanstack/react-query';
import { getTriage } from '@/api/patient';
import { pollInterval } from '@/lib/polling';
import type { TriageResult } from '@/api/schemas';

const isPending = (d: unknown): d is { status: 'pending' } =>
  typeof d === 'object' && d !== null && 'status' in d;

export function useTriage(consultationId: string) {
  return useQuery({
    queryKey: ['triage', consultationId],
    queryFn: async (): Promise<TriageResult | { status: 'pending' }> => getTriage(consultationId),
    refetchInterval: (q) => pollInterval(isPending(q.state.data), 1500),
    select: (d) => (isPending(d) ? undefined : (d as TriageResult)),
  });
}

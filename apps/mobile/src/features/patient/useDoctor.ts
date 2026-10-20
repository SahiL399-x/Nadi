import { useQuery } from '@tanstack/react-query';
import { getDoctor } from '@/api/patient';

export function useDoctor(did: string) {
  return useQuery({ queryKey: ['doctor', did], queryFn: () => getDoctor(did) });
}

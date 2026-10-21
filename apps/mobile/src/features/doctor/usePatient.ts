import { useQuery } from '@tanstack/react-query';
import { getPatient } from '@/api/doctorPortal';
export function usePatient(pid: string) {
  return useQuery({ queryKey: ['patient', pid], queryFn: () => getPatient(pid) });
}

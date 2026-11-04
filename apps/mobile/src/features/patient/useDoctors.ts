import { useQuery } from '@tanstack/react-query';
import { searchDoctors } from '@/api/patient';

export function useDoctors(specialty?: string, q?: string) {
  return useQuery({ queryKey: ['doctors', specialty, q], queryFn: () => searchDoctors({ specialty, q }) });
}

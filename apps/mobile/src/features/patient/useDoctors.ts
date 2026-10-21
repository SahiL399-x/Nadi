import { useQuery } from '@tanstack/react-query';
import { searchDoctors } from '@/api/patient';

export function useDoctors(specialty?: string) {
  return useQuery({ queryKey: ['doctors', specialty], queryFn: () => searchDoctors({ specialty }) });
}

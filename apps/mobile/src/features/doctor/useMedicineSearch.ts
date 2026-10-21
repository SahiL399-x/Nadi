import { useQuery } from '@tanstack/react-query';
import { searchMedicines } from '@/api/doctorPortal';

export function useMedicineSearch(q: string) {
  return useQuery({ queryKey: ['medicines', q], queryFn: () => searchMedicines(q), staleTime: 60000 });
}

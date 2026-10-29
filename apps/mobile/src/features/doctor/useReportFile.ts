import { useQuery } from '@tanstack/react-query';
import { getReportFile } from '@/api/doctorPortal';

export function useReportFile(patientId: string) {
  return useQuery({ queryKey: ['reportFile', patientId], queryFn: () => getReportFile(patientId) });
}

import { useQuery } from '@tanstack/react-query';
import { listDoctorPrescriptions, listLabReports } from '@/api/doctorPortal';

export function useDoctorPrescriptions(status: 'all' | 'active' | 'completed') {
  return useQuery({ queryKey: ['doctorPrescriptions', status], queryFn: () => listDoctorPrescriptions(status) });
}
export function useLabReports(status: 'all' | 'pending' | 'completed') {
  return useQuery({ queryKey: ['labReports', status], queryFn: () => listLabReports(status) });
}

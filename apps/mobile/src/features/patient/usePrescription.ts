import { useQuery } from '@tanstack/react-query';
import { getConsultation, getPrescription } from '@/api/patient';
import { pollInterval } from '@/lib/polling';

export function usePrescription(consultationId: string) {
  const consult = useQuery({
    queryKey: ['consultation', consultationId],
    queryFn: () => getConsultation(consultationId),
    refetchInterval: (q) => pollInterval(!q.state.data?.prescriptionId, 3000),
  });
  const prescriptionId = consult.data?.prescriptionId ?? null;
  const prescription = useQuery({
    queryKey: ['prescription', prescriptionId],
    queryFn: () => getPrescription(prescriptionId!),
    enabled: !!prescriptionId,
    refetchInterval: (q) => pollInterval(q.state.data?.status === 'PENDING', 3000),
  });
  return { prescriptionId, prescription: prescription.data, waiting: !prescriptionId };
}

import { useState } from 'react';
import { prescribe, type PrescriptionLineInput } from '@/api/doctor';

export function usePrescribe() {
  const [pending, setPending] = useState(false);
  const submit = async (cid: string, lines: PrescriptionLineInput[]): Promise<string> => {
    setPending(true);
    try { return (await prescribe(cid, lines)).prescriptionId; }
    finally { setPending(false); }
  };
  return { submit, pending };
}

import { useState } from 'react';
import { consent } from '@/api/patient';

export function useConsent() {
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState(false);
  const submit = async (prescriptionId: string, ids: string[]) => {
    setPending(true);
    try { await consent(prescriptionId, ids); setDone(true); }
    finally { setPending(false); }
  };
  return { submit, pending, done };
}

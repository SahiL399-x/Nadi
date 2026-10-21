import { useState } from 'react';
import { intake, type IntakeInput } from '@/api/patient';

export function useIntake() {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submit = async (input: IntakeInput): Promise<string> => {
    setPending(true); setError(null);
    try { const r = await intake(input); return r.consultationId; }
    catch (e) { setError('Could not submit. Check your connection.'); throw e; }
    finally { setPending(false); }
  };
  return { submit, pending, error };
}

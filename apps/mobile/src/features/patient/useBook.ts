import { useState } from 'react';
import { book } from '@/api/patient';

export function useBook() {
  const [pending, setPending] = useState(false);
  const confirm = async (consultationId: string, doctorId: string, slot: string): Promise<boolean> => {
    setPending(true);
    try { return (await book(consultationId, { doctorId, slot })).booked; }
    finally { setPending(false); }
  };
  return { confirm, pending };
}

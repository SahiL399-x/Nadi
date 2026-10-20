import { useState } from 'react';
import { refer } from '@/api/doctor';

export function useRefer() {
  const [pending, setPending] = useState(false);
  const submit = async (cid: string, toSpecialty: string, reason: string): Promise<boolean> => {
    setPending(true);
    try {
      return (await refer(cid, { toSpecialty, reason })).referred;
    } finally {
      setPending(false);
    }
  };
  return { submit, pending };
}

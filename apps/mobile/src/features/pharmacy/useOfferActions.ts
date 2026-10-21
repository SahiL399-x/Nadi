import { useState } from 'react';
import { acceptOffer, declineOffer } from '@/api/pharmacy';

type Result = 'accepted' | 'forwarded' | 'declined' | null;

export function useOfferActions() {
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<Result>(null);
  const accept = async (id: string) => {
    setPending(true);
    try { await acceptOffer(id); setResult('accepted'); } finally { setPending(false); }
  };
  const decline = async (id: string) => {
    setPending(true);
    try { const r = await declineOffer(id); setResult(r.forwarded ? 'forwarded' : 'declined'); }
    finally { setPending(false); }
  };
  return { accept, decline, pending, result };
}

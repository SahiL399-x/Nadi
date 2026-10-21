import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { setOrderStatus } from '@/api/pharmacyPortal';

export function useOrderTransition() {
  const qc = useQueryClient();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const advance = async (offerId: string, status: string): Promise<string> => {
    setPending(true);
    setError(null);
    try {
      const r = await setOrderStatus(offerId, status);
      await qc.invalidateQueries({ queryKey: ['orders'] });
      await qc.invalidateQueries({ queryKey: ['pharmacyStats'] });
      return r.status;
    } catch {
      setError('Could not update this order. Please try again.');
      return '';
    } finally {
      setPending(false);
    }
  };
  return { advance, pending, error };
}

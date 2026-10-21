import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { addNote, listNotes, type Note } from '@/api/doctorPortal';
export function useNotes(consultationId: string) {
  const qc = useQueryClient();
  const [pending, setPending] = useState(false);
  const q = useQuery({ queryKey: ['notes', consultationId], queryFn: () => listNotes(consultationId) });
  const add = async (text: string) => {
    setPending(true);
    try { await addNote(consultationId, text); await qc.invalidateQueries({ queryKey: ['notes', consultationId] }); }
    finally { setPending(false); }
  };
  const notes: Note[] = q.data ?? [];
  return { notes, add, pending };
}

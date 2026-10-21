import { useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getAvailability, putAvailability, type Availability } from '@/api/doctorPortal';

export function useAvailability() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ['availability'], queryFn: getAvailability });
  const [week, setWeek] = useState<Availability[]>([]);
  const [saving, setSaving] = useState(false);
  // Load server data into editable state once; a later refetch (e.g. on app refocus)
  // must not clobber the doctor's in-progress unsaved edits.
  const loaded = useRef(false);
  useEffect(() => { if (q.data && !loaded.current) { setWeek(q.data); loaded.current = true; } }, [q.data]);
  const toggle = (weekday: number) =>
    setWeek((w) => w.map((d) => (d.weekday === weekday ? { ...d, isOpen: !d.isOpen } : d)));
  const setField = (weekday: number, key: 'morning' | 'evening', value: string) =>
    setWeek((w) => w.map((d) => (d.weekday === weekday ? { ...d, [key]: value } : d)));
  const save = async () => {
    setSaving(true);
    try {
      await putAvailability(week);
      await qc.invalidateQueries({ queryKey: ['availability'] });
    } finally {
      setSaving(false);
    }
  };
  return { week, isLoading: q.isLoading, toggle, setField, save, saving };
}

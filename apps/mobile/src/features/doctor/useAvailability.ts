import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getAvailability, putAvailability, type Availability } from '@/api/doctorPortal';

export function useAvailability() {
  const q = useQuery({ queryKey: ['availability'], queryFn: getAvailability });
  const [week, setWeek] = useState<Availability[]>([]);
  const [saving, setSaving] = useState(false);
  useEffect(() => { if (q.data) setWeek(q.data); }, [q.data]);
  const toggle = (weekday: number) =>
    setWeek((w) => w.map((d) => (d.weekday === weekday ? { ...d, isOpen: !d.isOpen } : d)));
  const setField = (weekday: number, key: 'morning' | 'evening', value: string) =>
    setWeek((w) => w.map((d) => (d.weekday === weekday ? { ...d, [key]: value } : d)));
  const save = async () => { setSaving(true); try { await putAvailability(week); } finally { setSaving(false); } };
  return { week, isLoading: q.isLoading, toggle, setField, save, saving };
}

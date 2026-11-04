import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getDoctorProfile, updateDoctorProfile } from '@/api/doctorPortal';

export function useDoctorProfile() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ['doctorProfile'], queryFn: getDoctorProfile });
  const [saving, setSaving] = useState(false);
  const save = async (body: Parameters<typeof updateDoctorProfile>[0]) => {
    setSaving(true);
    try {
      await updateDoctorProfile(body);
      await qc.invalidateQueries({ queryKey: ['doctorProfile'] });
    } finally {
      setSaving(false);
    }
  };
  return { profile: q.data, isLoading: q.isLoading, save, saving };
}

import { useEffect } from 'react';
import { router, useLocalSearchParams } from 'expo-router';
import { VideoRoom } from '@/components/VideoRoom';
import { useSession } from '@/store/session';
import { notify } from '@/lib/notify';

export default function DoctorRoom() {
  const { cid } = useLocalSearchParams<{ cid: string }>();
  const userId = useSession((s) => s.userId);
  useEffect(() => { void notify('doctor', 'Video consultation', 'You joined the video room with your patient.'); }, []);
  return <VideoRoom consultationId={cid!} displayName={`Doctor ${userId ?? ''}`.trim()} onClose={() => router.back()} />;
}

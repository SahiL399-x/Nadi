import { useEffect } from 'react';
import { router, useLocalSearchParams } from 'expo-router';
import { VideoRoom } from '@/components/VideoRoom';
import { useSession } from '@/store/session';
import { notify } from '@/lib/notify';

export default function Consultation() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const userId = useSession((s) => s.userId);
  useEffect(() => { void notify('patient', 'Video consultation', 'You joined the video room.'); }, []);
  return <VideoRoom consultationId={id!} displayName={`Patient ${userId ?? ''}`.trim()} onClose={() => router.back()} />;
}

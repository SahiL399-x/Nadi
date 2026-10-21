import { router, useLocalSearchParams } from 'expo-router';
import { VideoRoom } from '@/components/VideoRoom';
import { useSession } from '@/store/session';

export default function Consultation() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const userId = useSession((s) => s.userId);
  return <VideoRoom consultationId={id!} displayName={`Patient ${userId ?? ''}`.trim()} onClose={() => router.back()} />;
}

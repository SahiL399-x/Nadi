import { router, useLocalSearchParams } from 'expo-router';
import { VideoRoom } from '@/components/VideoRoom';
import { useSession } from '@/store/session';

export default function DoctorRoom() {
  const { cid } = useLocalSearchParams<{ cid: string }>();
  const userId = useSession((s) => s.userId);
  return <VideoRoom consultationId={cid!} displayName={`Doctor ${userId ?? ''}`.trim()} onClose={() => router.back()} />;
}

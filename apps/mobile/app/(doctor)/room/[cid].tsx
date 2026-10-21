import { router, useLocalSearchParams } from 'expo-router';
import { JitsiRoom } from '@/components/JitsiRoom';
import { useSession } from '@/store/session';

export default function DoctorRoom() {
  const { cid } = useLocalSearchParams<{ cid: string }>();
  const userId = useSession((s) => s.userId);
  return <JitsiRoom consultationId={cid!} displayName={`Doctor ${userId ?? ''}`.trim()} onClose={() => router.back()} />;
}

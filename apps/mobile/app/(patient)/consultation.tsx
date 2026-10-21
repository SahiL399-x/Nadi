import { router, useLocalSearchParams } from 'expo-router';
import { JitsiRoom } from '@/components/JitsiRoom';
import { useSession } from '@/store/session';

export default function Consultation() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const userId = useSession((s) => s.userId);
  return <JitsiRoom consultationId={id!} displayName={`Patient ${userId ?? ''}`.trim()} onClose={() => router.back()} />;
}

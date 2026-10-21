import { useState } from 'react';
import { Text, View } from 'react-native';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { useNotes } from '@/features/doctor/useNotes';
import { colors, spacing, type as t } from '@/theme/tokens';

export function NotesPanel({ consultationId }: { consultationId: string }) {
  const { notes, add, pending } = useNotes(consultationId);
  const [text, setText] = useState('');
  const save = async () => { if (!text.trim()) return; await add(text.trim()); setText(''); };
  return (
    <Card>
      <Text style={{ fontSize: t.sm, color: colors.navy, fontWeight: '800' }}>MY NOTES</Text>
      <Text style={{ fontSize: t.xs, color: colors.textMuted, marginBottom: spacing.sm }}>Private to you.</Text>
      {notes.length === 0 ? (
        <Text style={{ fontSize: t.sm, color: colors.textMuted }}>No notes yet.</Text>
      ) : notes.map((n) => (
        <Text key={n.id} style={{ fontSize: t.sm, color: colors.text, marginBottom: 4 }}>• {n.text}</Text>
      ))}
      <View style={{ height: spacing.sm }} />
      <Input value={text} onChangeText={setText} multiline placeholder="Add a private note…" />
      <View style={{ height: spacing.sm }} />
      <Button title="Save note" color={colors.navy} loading={pending} disabled={!text.trim()} onPress={save} />
    </Card>
  );
}

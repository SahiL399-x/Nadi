import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import {
  AudioSession,
  LiveKitRoom,
  VideoTrack,
  isTrackReference,
  registerGlobals,
  useTracks,
} from '@livekit/react-native';
import { Track } from 'livekit-client';
import { Button } from '@/components/ui/Button';
import { getVideoToken } from '@/api/video';
import { colors, spacing, type as t } from '@/theme/tokens';

// Install the WebRTC globals LiveKit needs, once, before any room mounts.
registerGlobals();

type Props = { consultationId: string; displayName: string; onClose: () => void };

export function VideoRoom({ consultationId, onClose }: Props) {
  const [conn, setConn] = useState<{ url: string; token: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fetch a short-lived join token from the backend for this consultation's room.
  useEffect(() => {
    let active = true;
    getVideoToken(consultationId)
      .then((r) => { if (active) setConn({ url: r.url, token: r.token }); })
      .catch(() => { if (active) setError('Could not start the video call.'); });
    return () => { active = false; };
  }, [consultationId]);

  // Route audio to the earpiece/speaker correctly for the duration of the call.
  useEffect(() => {
    let started = false;
    AudioSession.startAudioSession().then(() => { started = true; }).catch(() => { /* no-op */ });
    return () => { if (started) AudioSession.stopAudioSession(); };
  }, []);

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={{ fontSize: t.h2, color: colors.text, fontWeight: '700' }}>Video consultation</Text>
        <Text style={{ fontSize: t.sm, color: colors.textMuted }}>{error}</Text>
        <Button title="Go back" onPress={onClose} />
      </View>
    );
  }
  if (!conn) {
    return (
      <View style={styles.center}>
        <Text style={{ fontSize: t.sm, color: colors.textMuted }}>Connecting to the secure room…</Text>
      </View>
    );
  }

  return (
    <View style={{ flex: 1 }}>
      <LiveKitRoom
        serverUrl={conn.url}
        token={conn.token}
        connect
        audio
        video
        onDisconnected={onClose}
      >
        <Stage />
      </LiveKitRoom>
    </View>
  );
}

// Renders every camera track (local + remote) stacked to fill the screen.
function Stage() {
  const tracks = useTracks([Track.Source.Camera]);
  return (
    <View style={styles.stage}>
      {tracks.map((track, i) =>
        isTrackReference(track) ? (
          <VideoTrack key={`${track.participant.sid}-${i}`} trackRef={track} style={styles.tile} />
        ) : null,
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: spacing.xl, gap: spacing.md },
  stage: { flex: 1, backgroundColor: colors.text },
  tile: { flex: 1 },
});

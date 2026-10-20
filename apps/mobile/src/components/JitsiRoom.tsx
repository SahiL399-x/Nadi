import { useState } from 'react';
import { Text, View } from 'react-native';
import * as WebBrowser from 'expo-web-browser';
import { Button } from '@/components/ui';
import { roomName, roomUrl } from '@/lib/room';
import { colors, spacing, type as t } from '@/theme/tokens';

// Load the native SDK defensively so the screen still works (via browser) when it is absent.
let JitsiMeeting: React.ComponentType<Record<string, unknown>> | null = null;
try { JitsiMeeting = require('@jitsi/react-native-sdk').JitsiMeeting; } catch { JitsiMeeting = null; }

type Props = { consultationId: string; displayName: string; onClose: () => void };

export function JitsiRoom({ consultationId, displayName, onClose }: Props) {
  const [browserError, setBrowserError] = useState<string | null>(null);
  const openInBrowser = async () => {
    try { await WebBrowser.openBrowserAsync(roomUrl(consultationId)); }
    catch { setBrowserError('Could not open the video call.'); }
  };

  if (!JitsiMeeting) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', padding: spacing.xl, gap: spacing.md }}>
        <Text style={{ fontSize: t.h2, color: colors.text, fontWeight: '700' }}>Video consultation</Text>
        <Text style={{ fontSize: t.sm, color: colors.textMuted }}>
          In-app video needs the installed dev build. Open the secure room in your browser instead.
        </Text>
        <Button title="Open video in browser" onPress={openInBrowser} />
        {browserError ? <Text style={{ color: colors.emergency, fontSize: t.sm }}>{browserError}</Text> : null}
      </View>
    );
  }

  const Meeting = JitsiMeeting;
  return (
    <View style={{ flex: 1 }}>
      <Meeting
        style={{ flex: 1 }}
        room={roomName(consultationId)}
        serverURL="https://meet.jit.si/"
        userInfo={{ displayName, email: '' }}
        config={{ subject: 'NADI consultation', startWithAudioMuted: false, startWithVideoMuted: false }}
        flags={{ 'invite.enabled': false, 'meeting-password.enabled': false, 'pip.enabled': true }}
        eventListeners={{ onReadyToClose: onClose }}
      />
    </View>
  );
}

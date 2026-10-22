import { useNotifications } from '@/store/notifications';

let seq = 0;

// Role-aware notification: always recorded in the in-app feed (the bell), and
// also fired as an OS notification when expo-notifications is available (after
// the dev build that adds it). Defensive so it never crashes beforehand.
export async function notify(role: string, title: string, body: string): Promise<void> {
  useNotifications.getState().add({ id: `n${Date.now()}-${seq++}`, role, title, body, at: Date.now() });
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const N = require('expo-notifications');
    await N.scheduleNotificationAsync({ content: { title, body }, trigger: null });
  } catch {
    /* module absent (pre-rebuild) or permission not granted — in-app feed still works */
  }
}

// Request OS notification permission; safe no-op if the module isn't present yet.
export async function requestNotifications(): Promise<void> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const N = require('expo-notifications');
    await N.requestPermissionsAsync();
  } catch {
    /* not available until the dev build */
  }
}

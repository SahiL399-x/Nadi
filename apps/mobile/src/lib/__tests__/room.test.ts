import { roomName, roomUrl } from '@/lib/room';

test('builds a stable per-consultation room name and url', () => {
  expect(roomName('abc-123')).toBe('nadi-abc-123');
  expect(roomUrl('abc-123')).toBe('https://meet.jit.si/nadi-abc-123');
});

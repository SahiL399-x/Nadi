export function roomName(consultationId: string): string {
  return `nadi-${consultationId}`;
}

export function roomUrl(consultationId: string): string {
  return `https://meet.jit.si/${roomName(consultationId)}`;
}

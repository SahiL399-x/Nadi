import { z } from 'zod';
import { api } from '@/api/client';

export const VideoTokenSchema = z.object({
  url: z.string(),
  token: z.string(),
  room: z.string(),
});
export type VideoToken = z.infer<typeof VideoTokenSchema>;

// Both patient and doctor call this for the same consultation and meet in room
// nadi-{consultationId}. The server embeds the room + identity in the token.
export function getVideoToken(consultationId: string): Promise<VideoToken> {
  return api.post('/v1/video/token', { consultationId }, VideoTokenSchema);
}

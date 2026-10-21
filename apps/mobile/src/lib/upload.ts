import * as ImageManipulator from 'expo-image-manipulator';
import { signUpload } from '@/api/patient';

export class UploadError extends Error {
  constructor(public kind: 'storage' | 'network', message: string) { super(message); }
}

export async function uploadReport(localUri: string): Promise<string> {
  const edited = await ImageManipulator.manipulateAsync(
    localUri, [{ resize: { width: 1600 } }],
    { compress: 0.75, format: ImageManipulator.SaveFormat.WEBP },
  );
  let bytes: Blob;
  try {
    const r = await fetch(edited.uri);
    bytes = await r.blob();
  } catch { throw new UploadError('network', 'could not read image'); }

  const { url, objectKey } = await signUpload();
  let put: Response;
  try {
    put = await fetch(url, { method: 'PUT', headers: { 'content-type': 'image/webp' }, body: bytes });
  } catch { throw new UploadError('network', 'could not reach storage'); }
  if (!put.ok) throw new UploadError('storage', `storage rejected upload (${put.status})`);
  return objectKey;
}

import * as ImageManipulator from 'expo-image-manipulator';
import { signUpload } from '@/api/patient';

export class UploadError extends Error {
  constructor(public kind: 'storage' | 'network', message: string) { super(message); }
}

type UploadOpts = { kind: 'image' | 'pdf'; source: 'scan' | 'upload' };

export async function uploadReport(localUri: string, opts: UploadOpts): Promise<string> {
  let body: Blob;
  let contentType: string;
  let ext: 'webp' | 'pdf';

  if (opts.kind === 'pdf') {
    ext = 'pdf';
    contentType = 'application/pdf';
    try {
      const r = await fetch(localUri);
      body = await r.blob();
    } catch { throw new UploadError('network', 'could not read file'); }
  } else {
    ext = 'webp';
    contentType = 'image/webp';
    const edited = await ImageManipulator.manipulateAsync(
      localUri, [{ resize: { width: 1600 } }],
      { compress: 0.75, format: ImageManipulator.SaveFormat.WEBP },
    );
    try {
      const r = await fetch(edited.uri);
      body = await r.blob();
    } catch { throw new UploadError('network', 'could not read image'); }
  }

  const { url, objectKey } = await signUpload({ source: opts.source, ext });
  let put: Response;
  try {
    put = await fetch(url, { method: 'PUT', headers: { 'content-type': contentType }, body });
  } catch { throw new UploadError('network', 'could not reach storage'); }
  if (!put.ok) throw new UploadError('storage', `storage rejected upload (${put.status})`);
  return objectKey;
}

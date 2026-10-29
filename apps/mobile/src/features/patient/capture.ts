export function classifyPicked(name: string | undefined, mimeType?: string): 'image' | 'pdf' {
  if (mimeType === 'application/pdf') return 'pdf';
  if (name && name.toLowerCase().endsWith('.pdf')) return 'pdf';
  return 'image';
}

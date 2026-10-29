import { useCallback, useState } from 'react';
import { uploadReport } from '@/lib/upload';

type Item = { id: string; uri: string; kind: 'image' | 'pdf'; source: 'scan' | 'upload';
              status: 'uploading' | 'done' | 'error'; objectKey?: string };
let seq = 0;

export function useReportUploads() {
  const [items, setItems] = useState<Item[]>([]);
  const patch = (id: string, p: Partial<Item>) =>
    setItems((xs) => xs.map((x) => (x.id === id ? { ...x, ...p } : x)));

  const run = useCallback(async (it: Item) => {
    patch(it.id, { status: 'uploading' });
    try { patch(it.id, { status: 'done', objectKey: await uploadReport(it.uri, { kind: it.kind, source: it.source }) }); }
    catch { patch(it.id, { status: 'error' }); }
  }, []);

  const add = useCallback((uri: string, kind: 'image' | 'pdf', source: 'scan' | 'upload') => {
    const id = `r${seq++}`;
    const it: Item = { id, uri, kind, source, status: 'uploading' };
    setItems((xs) => [...xs, it]);
    void run(it);
  }, [run]);

  const remove = useCallback((id: string) => setItems((xs) => xs.filter((x) => x.id !== id)), []);
  const retry = useCallback((id: string) => {
    const it = items.find((x) => x.id === id);
    if (it) void run(it);
  }, [items, run]);

  const allSettled = items.every((x) => x.status === 'done');
  const objectKeys = items.filter((x) => x.objectKey).map((x) => x.objectKey!) as string[];
  return { items, add, remove, retry, allSettled, objectKeys };
}

import { useCallback, useState } from 'react';
import { uploadReport } from '@/lib/upload';

type Item = { id: string; uri: string; status: 'uploading' | 'done' | 'error'; objectKey?: string };
let seq = 0;

export function useReportUploads() {
  const [items, setItems] = useState<Item[]>([]);
  const patch = (id: string, p: Partial<Item>) =>
    setItems((xs) => xs.map((x) => (x.id === id ? { ...x, ...p } : x)));

  const run = useCallback(async (id: string, uri: string) => {
    patch(id, { status: 'uploading' });
    try { patch(id, { status: 'done', objectKey: await uploadReport(uri) }); }
    catch { patch(id, { status: 'error' }); }
  }, []);

  const add = useCallback((uri: string) => {
    const id = `r${seq++}`;
    setItems((xs) => [...xs, { id, uri, status: 'uploading' }]);
    void run(id, uri);
  }, [run]);

  const remove = useCallback((id: string) => setItems((xs) => xs.filter((x) => x.id !== id)), []);
  const retry = useCallback((id: string) => {
    const it = items.find((x) => x.id === id);
    if (it) void run(id, it.uri);
  }, [items, run]);

  const allSettled = items.every((x) => x.status === 'done');
  const objectKeys = items.filter((x) => x.objectKey).map((x) => x.objectKey!) as string[];
  return { items, add, remove, retry, allSettled, objectKeys };
}

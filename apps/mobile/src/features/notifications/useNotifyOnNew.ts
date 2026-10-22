import { useEffect, useRef } from 'react';
import { notify } from '@/lib/notify';

// Fire a role notification when a polled list gains items it didn't have before.
// The first batch is seeded silently (so existing data doesn't spam on open).
export function useNotifyOnNew<T>(
  items: T[] | undefined,
  keyOf: (x: T) => string,
  role: string,
  build: (x: T) => { title: string; body: string },
): void {
  const seen = useRef<Set<string> | null>(null);
  useEffect(() => {
    if (!items) return;
    if (seen.current === null) {
      seen.current = new Set(items.map(keyOf));
      return;
    }
    for (const it of items) {
      const k = keyOf(it);
      if (!seen.current.has(k)) {
        seen.current.add(k);
        const { title, body } = build(it);
        void notify(role, title, body);
      }
    }
  }, [items, keyOf, role, build]);
}

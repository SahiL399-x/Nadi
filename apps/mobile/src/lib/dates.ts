export function isoDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export function dayChips(): { label: string; iso: string }[] {
  const base = new Date();
  const mk = (offset: number, label: string) => {
    const d = new Date(base);
    d.setDate(base.getDate() + offset);
    return { label, iso: isoDate(d) };
  };
  return [mk(0, 'Today'), mk(1, 'Tomorrow'), mk(2, isoDate(new Date(base.getTime() + 2 * 86400000)).slice(5))];
}

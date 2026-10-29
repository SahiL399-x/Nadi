import type { ExtractionField, ReportView } from '@/api/doctorPortal';

export function isAbnormal(f: ExtractionField): boolean {
  return f.flag === 'L' || f.flag === 'H';
}

export function abnormalFirst(reports: ReportView[]): ExtractionField[] {
  const all = reports.flatMap((r) => r.fields);
  return [...all.filter(isAbnormal), ...all.filter((f) => !isAbnormal(f))];
}

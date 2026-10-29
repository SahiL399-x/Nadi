import { abnormalFirst, isAbnormal } from '@/features/doctor/reportAggregate';

const field = (name: string, flag?: string) => ({ testNameNormalized: name, flag });
const report = (fields: any[]) =>
  ({ reportId: 'r', kind: 'image', imageUrl: '', date: '', needsReview: false, extracted: true, fields } as any);

test('isAbnormal is true only for L or H', () => {
  expect(isAbnormal(field('x', 'L'))).toBe(true);
  expect(isAbnormal(field('x', 'H'))).toBe(true);
  expect(isAbnormal(field('x', 'N'))).toBe(false);
  expect(isAbnormal(field('x'))).toBe(false);
});

test('abnormalFirst orders flagged fields before normal, across reports', () => {
  const out = abnormalFirst([
    report([field('Normal1', 'N'), field('Low1', 'L')]),
    report([field('High1', 'H'), field('Normal2')]),
  ]);
  expect(out.slice(0, 2).map((f) => f.testNameNormalized)).toEqual(['Low1', 'High1']);
  expect(out).toHaveLength(4);
});

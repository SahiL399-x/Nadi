import { classifyPicked } from '@/features/patient/capture';

test('classifies pdf by mime', () => {
  expect(classifyPicked('r.pdf', 'application/pdf')).toBe('pdf');
});
test('classifies pdf by extension when mime missing', () => {
  expect(classifyPicked('scan_001.PDF', undefined)).toBe('pdf');
});
test('defaults to image', () => {
  expect(classifyPicked('photo.jpg', 'image/jpeg')).toBe('image');
  expect(classifyPicked(undefined, undefined)).toBe('image');
});

import { render } from '@testing-library/react-native';
import { ReportCard } from '@/components/doctor/ReportCard';

const base = { reportId: '1', imageUrl: 'http://x/y.webp', date: '29 Oct 2026',
  needsReview: false, extracted: true, fields: [] };

test('renders an image thumbnail for image kind', async () => {
  const { getByTestId, queryByTestId } = await render(
    <ReportCard report={{ ...base, kind: 'image' } as any} label="Lab report 1" onOpen={() => {}} />);
  expect(getByTestId('report-thumb')).toBeTruthy();
  expect(queryByTestId('report-pdf')).toBeNull();
});

test('renders a PDF placeholder for pdf kind', async () => {
  const { getByTestId } = await render(
    <ReportCard report={{ ...base, kind: 'pdf' } as any} label="Lab report 1" onOpen={() => {}} />);
  expect(getByTestId('report-pdf')).toBeTruthy();
});

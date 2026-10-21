import { render, screen } from '@testing-library/react-native';
import { NadiNote } from '@/components/NadiNote';

const triage = {
  acuity: 'URGENT', acuityConfidence: 0.82,
  specialties: [{ name: 'Cardiology', score: 0.8 }], drivers: [{ feature: 'chest pain', contribution: 0.5 }],
  labs: [], redFlags: [], modelVersion: 'stub',
} as any;

test('shows acuity label and confidence percent', async () => {
  await render(<NadiNote triage={triage} />);
  expect(screen.getByText('Urgent')).toBeOnTheScreen();
  expect(screen.getByText(/82%/)).toBeOnTheScreen();
});

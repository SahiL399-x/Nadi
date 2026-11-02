import { render, screen } from '@testing-library/react-native';
import { NadiNote } from '@/components/NadiNote';

const triage = {
  specialties: [{ name: 'Cardiology', score: 0.8 }],
  labs: [], modelVersion: 'stub',
} as any;

test('shows the suggested specialty', async () => {
  await render(<NadiNote triage={triage} />);
  expect(screen.getByText(/Cardiology/)).toBeOnTheScreen();
});

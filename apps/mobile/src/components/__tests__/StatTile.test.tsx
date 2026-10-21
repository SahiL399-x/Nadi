import { render, screen } from '@testing-library/react-native';
import { StatTile } from '@/components/StatTile';

test('renders a label and value', async () => {
  await render(<StatTile label="Prescriptions Issued" value={6} />);
  expect(screen.getByText('Prescriptions Issued')).toBeOnTheScreen();
  expect(screen.getByText('6')).toBeOnTheScreen();
});

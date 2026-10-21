import { render, screen } from '@testing-library/react-native';
import { AcuityBadge } from '@/components/ui/AcuityBadge';

test('shows the acuity text label, not colour alone', async () => {
  await render(<AcuityBadge acuity="EMERGENCY" />);
  expect(screen.getByText('Emergency')).toBeOnTheScreen();
});

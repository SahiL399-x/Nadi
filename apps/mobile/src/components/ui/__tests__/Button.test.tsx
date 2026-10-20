import { fireEvent, render, screen } from '@testing-library/react-native';
import { Button } from '@/components/ui/Button';

test('calls onPress; disabled when loading', async () => {
  const onPress = jest.fn();
  const { rerender } = await render(<Button title="Book" onPress={onPress} />);
  fireEvent.press(screen.getByText('Book'));
  expect(onPress).toHaveBeenCalledTimes(1);
  await rerender(<Button title="Book" onPress={onPress} loading />);
  fireEvent.press(screen.getByTestId('button'));
  expect(onPress).toHaveBeenCalledTimes(1);
});

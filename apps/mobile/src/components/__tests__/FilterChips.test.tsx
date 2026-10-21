import { fireEvent, render, screen } from '@testing-library/react-native';
import { FilterChips } from '@/components/FilterChips';

test('calls onChange with the chosen value', async () => {
  const onChange = jest.fn();
  await render(<FilterChips options={[{ label: 'All', value: 'all' }, { label: 'Active', value: 'active' }]}
    value="all" onChange={onChange} />);
  fireEvent.press(screen.getByText('Active'));
  expect(onChange).toHaveBeenCalledWith('active');
});

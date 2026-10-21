import { render, waitFor } from '@testing-library/react-native';
import Index from '../app/index';

jest.mock('expo-router', () => ({ Redirect: () => null }));

test('launch gate renders without crashing when signed out', async () => {
  await render(<Index />);
  await waitFor(() => {});
});

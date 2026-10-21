import { render, screen } from '@testing-library/react-native';
import { Text, View } from 'react-native';

test('nativewind className renders without crashing', async () => {
  await render(
    <View className="p-4">
      <Text className="text-lg">hi</Text>
    </View>
  );
  expect(screen.getByText('hi')).toBeOnTheScreen();
});

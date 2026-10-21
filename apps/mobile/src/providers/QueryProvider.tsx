import { QueryClient, QueryClientProvider, focusManager } from '@tanstack/react-query';
import { useEffect } from 'react';
import { AppState, type AppStateStatus } from 'react-native';

const client = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 5000 } },
});

export function QueryProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const sub = AppState.addEventListener('change', (status: AppStateStatus) => {
      focusManager.setFocused(status === 'active');
    });
    return () => sub.remove();
  }, []);
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

import { createContext, useContext } from 'react';
import { roleTheme, type Role } from '@/theme/tokens';

const ThemeCtx = createContext(roleTheme('patient'));
export const useTheme = () => useContext(ThemeCtx);
export function ThemeProvider({ role, children }: { role: Role; children: React.ReactNode }) {
  return <ThemeCtx.Provider value={roleTheme(role)}>{children}</ThemeCtx.Provider>;
}

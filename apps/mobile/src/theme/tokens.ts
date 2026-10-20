import type { Acuity } from '@nadi/shared-types';

export const colors = {
  // brand (spec §4 chosen palette)
  seaGreen: '#2E8B57', brightGreen: '#4BB543', lightGrey: '#F4F4F4',
  navy: '#003366', lightBlue: '#A2C2E1',
  surface: '#FFFFFF', border: '#E4E6E1', text: '#14201C', textMuted: '#5E6B66',
  // acuity (ProjectPlan §12 — kept)
  routine: '#15803D', priority: '#CA8A04', urgent: '#EA580C', emergency: '#B91C1C',
} as const;

export const radii = { sm: 8, md: 14, lg: 20, pill: 999 } as const;
export const spacing = { xs: 4, sm: 8, md: 16, lg: 24, xl: 32, xxl: 48 } as const;
export const type = { h1: 30, h2: 24, h3: 20, body: 17, sm: 15, xs: 13 } as const;

const ACUITY: Record<Acuity, string> = {
  ROUTINE: colors.routine, PRIORITY: colors.priority,
  URGENT: colors.urgent, EMERGENCY: colors.emergency,
};
export const acuityColor = (a: Acuity): string => ACUITY[a];

export type Role = 'patient' | 'doctor' | 'pharmacy';
export function roleTheme(role: Role) {
  if (role === 'patient') {
    return { primary: colors.seaGreen, primaryFg: '#FFFFFF', accentBg: colors.lightGrey };
  }
  return { primary: colors.navy, primaryFg: '#FFFFFF', accentBg: colors.lightBlue };
}

import type { Acuity } from '@nadi/shared-types';

export const colors = {
  // brand — Nadi logo green for patients, navy for doctors, orange for pharmacy
  brightGreen: '#22B24C', seaGreen: '#2E8B57', green700: '#15803D',
  navy: '#003366', navy600: '#1E4E86', lightBlue: '#A2C2E1',
  orange: '#F97316', orange700: '#C2410C',
  // neutrals
  white: '#FFFFFF', surface: '#FFFFFF', pageBg: '#F3F4FB', lightGrey: '#F4F4F4',
  border: '#E6E8F0', text: '#14201C', textMuted: '#5E6B66', textFaint: '#8A958F',
  // soft role tints (card/section backgrounds)
  greenTint: '#E7F8EC', navyTint: '#E8F0FB', orangeTint: '#FFF1E6',
  // acuity (ProjectPlan §12 — kept)
  routine: '#15803D', priority: '#CA8A04', urgent: '#EA580C', emergency: '#B91C1C',
} as const;

export const radii = { sm: 8, md: 14, lg: 20, xl: 28, pill: 999 } as const;
export const spacing = { xs: 4, sm: 8, md: 16, lg: 24, xl: 32, xxl: 48 } as const;
export const type = { h1: 30, h2: 24, h3: 20, body: 17, sm: 15, xs: 13 } as const;

// Soft, tinted card shadow (RN style object) — matches the design-skill guidance.
export const shadow = {
  card: {
    shadowColor: '#1B2A4A', shadowOpacity: 0.08, shadowRadius: 16,
    shadowOffset: { width: 0, height: 6 }, elevation: 3,
  },
} as const;

const ACUITY: Record<Acuity, string> = {
  ROUTINE: colors.routine, PRIORITY: colors.priority,
  URGENT: colors.urgent, EMERGENCY: colors.emergency,
};
export const acuityColor = (a: Acuity): string => ACUITY[a];

export type Role = 'patient' | 'doctor' | 'pharmacy';
export type RoleTheme = {
  primary: string; primaryFg: string; tint: string; accentBg: string;
};
export function roleTheme(role: Role): RoleTheme {
  if (role === 'doctor') {
    return { primary: colors.navy, primaryFg: colors.white, tint: colors.navyTint, accentBg: colors.lightBlue };
  }
  if (role === 'pharmacy') {
    return { primary: colors.orange, primaryFg: colors.white, tint: colors.orangeTint, accentBg: colors.lightGrey };
  }
  return { primary: colors.brightGreen, primaryFg: colors.white, tint: colors.greenTint, accentBg: colors.lightGrey };
}

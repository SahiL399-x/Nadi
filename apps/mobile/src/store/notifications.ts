import { create } from 'zustand';

export type AppNotification = { id: string; role: string; title: string; body: string; at: number };

type State = {
  items: AppNotification[];
  add: (n: AppNotification) => void;
  clear: () => void;
};

export const useNotifications = create<State>((set) => ({
  items: [],
  add: (n) => set((s) => ({ items: [n, ...s.items].slice(0, 50) })),
  clear: () => set({ items: [] }),
}));

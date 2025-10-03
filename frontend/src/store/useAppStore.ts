/**
 * Основной store приложения
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type { EngineStatus, Theme } from '../types';

// Define AppNotification locally to avoid conflicts
interface AppNotification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  duration?: number;
  timestamp: number;
}

interface AppState {
  // Engine state
  engineStatus: EngineStatus | null;
  isEngineRunning: boolean;
  selectedPreset: string | null;
  
  // UI state
  theme: Theme;
  sidebarCollapsed: boolean;
  notifications: AppNotification[];
  
  // Connection state
  isConnected: boolean;
  lastHeartbeat: number | null;
  
  // Actions
  setEngineStatus: (status: EngineStatus | null) => void;
  setIsEngineRunning: (running: boolean) => void;
  setSelectedPreset: (preset: string | null) => void;
  setTheme: (theme: Theme) => void;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  addNotification: (notification: Omit<AppNotification, 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
  setConnected: (connected: boolean) => void;
  setLastHeartbeat: (timestamp: number) => void;
}

const defaultTheme: Theme = {
  mode: 'light',
  primary: '#0d6efd',
  secondary: '#6c757d',
  success: '#198754',
  warning: '#ffc107',
  error: '#dc3545',
};

export const useAppStore = create<AppState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        engineStatus: null,
        isEngineRunning: false,
        selectedPreset: null,
        theme: defaultTheme,
        sidebarCollapsed: false,
        notifications: [],
        isConnected: false,
        lastHeartbeat: null,

        // Actions
        setEngineStatus: (status) => {
          set(() => ({
            engineStatus: status,
            isEngineRunning: status?.state === 'RUNNING',
          }));
        },

        setIsEngineRunning: (running) => {
          set({ isEngineRunning: running });
        },

        setSelectedPreset: (preset) => {
          set({ selectedPreset: preset });
        },

        setTheme: (theme) => {
          set({ theme });
        },

        toggleSidebar: () => {
          set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed }));
        },

        setSidebarCollapsed: (collapsed) => {
          set({ sidebarCollapsed: collapsed });
        },

        addNotification: (notification) => {
          const newNotification: AppNotification = {
            ...notification,
            id: Math.random().toString(36).substr(2, 9),
            timestamp: Date.now(),
          };
          
          set((state) => ({
            notifications: [...state.notifications, newNotification],
          }));

          // Auto-remove notification after duration
          if (notification.duration && notification.duration > 0) {
            setTimeout(() => {
              get().removeNotification(newNotification.id);
            }, notification.duration);
          }
        },

        removeNotification: (id) => {
          set((state) => ({
            notifications: state.notifications.filter((n) => n.id !== id),
          }));
        },

        clearNotifications: () => {
          set({ notifications: [] });
        },

        setConnected: (connected) => {
          set({ isConnected: connected });
        },

        setLastHeartbeat: (timestamp) => {
          set({ lastHeartbeat: timestamp });
        },
      }),
      {
        name: 'breakout-bot-store',
        partialize: (state) => ({
          theme: state.theme,
          sidebarCollapsed: state.sidebarCollapsed,
          selectedPreset: state.selectedPreset,
        }),
      }
    ),
    {
      name: 'breakout-bot-store',
    }
  )
);

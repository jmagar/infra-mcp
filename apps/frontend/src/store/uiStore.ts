import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

type Theme = 'light' | 'dark' | 'system';

interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  timestamp: Date;
  duration?: number;
}

interface UIStore {
  // Theme
  theme: Theme;
  
  // Sidebar
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
  
  // Notifications
  notifications: Notification[];
  
  // Loading states
  globalLoading: boolean;
  
  // Preferences
  preferences: {
    autoRefresh: boolean;
    refreshInterval: number;
    compactMode: boolean;
    showMetricTrends: boolean;
  };
  
  // Actions
  setTheme: (theme: Theme) => void;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
  setGlobalLoading: (loading: boolean) => void;
  updatePreferences: (updates: Partial<UIStore['preferences']>) => void;
}

export const useUIStore = create<UIStore>()(
  devtools(
    persist(
      (set) => ({
        // Initial state
        theme: 'system',
        sidebarOpen: false,
        sidebarCollapsed: false,
        notifications: [],
        globalLoading: false,
        preferences: {
          autoRefresh: true,
          refreshInterval: 30000, // 30 seconds
          compactMode: false,
          showMetricTrends: true,
        },

        // Actions
        setTheme: (theme) => set({ theme }),
        
        toggleSidebar: () =>
          set((state) => ({ sidebarOpen: !state.sidebarOpen })),
        
        setSidebarCollapsed: (collapsed) =>
          set({ sidebarCollapsed: collapsed }),
        
        addNotification: (notification) => {
          const id = `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
          const newNotification: Notification = {
            ...notification,
            id,
            timestamp: new Date(),
          };
          
          set((state) => ({
            notifications: [...state.notifications, newNotification],
          }));
          
          // Auto-remove notification after duration
          if (notification.duration !== 0) {
            const duration = notification.duration || 5000;
            setTimeout(() => {
              set((state) => ({
                notifications: state.notifications.filter((n) => n.id !== id),
              }));
            }, duration);
          }
        },
        
        removeNotification: (id) =>
          set((state) => ({
            notifications: state.notifications.filter((n) => n.id !== id),
          })),
        
        clearNotifications: () => set({ notifications: [] }),
        
        setGlobalLoading: (loading) => set({ globalLoading: loading }),
        
        updatePreferences: (updates) =>
          set((state) => ({
            preferences: { ...state.preferences, ...updates },
          })),
      }),
      {
        name: 'ui-store',
        partialize: (state) => ({
          theme: state.theme,
          sidebarCollapsed: state.sidebarCollapsed,
          preferences: state.preferences,
        }),
      }
    ),
    {
      name: 'ui-store',
    }
  )
);
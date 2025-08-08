import { createContext, useContext, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { useWebSocket } from '@/hooks/useWebSocket';

export interface NotificationAlert {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: string;
  device?: string;
  service?: string;
  auto_dismiss?: boolean;
}

export interface NotificationContextType {
  showToast: (type: 'success' | 'error' | 'warning' | 'info', message: string, title?: string) => void;
  showAlert: (alert: Omit<NotificationAlert, 'id' | 'timestamp'>) => void;
  dismissAlert: (id: string) => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
}

interface NotificationProviderProps {
  children: React.ReactNode;
}

export function NotificationProvider({ children }: NotificationProviderProps) {
  // WebSocket connection for real-time alerts
  const { data: alertData } = useWebSocket('ws://localhost:9101/ws/alerts');

  const showToast = useCallback((
    type: 'success' | 'error' | 'warning' | 'info',
    message: string,
    title?: string
  ) => {
    const toastOptions = {
      description: message,
      duration: type === 'error' ? 6000 : 4000,
    };

    switch (type) {
      case 'success':
        toast.success(title || 'Success', toastOptions);
        break;
      case 'error':
        toast.error(title || 'Error', toastOptions);
        break;
      case 'warning':
        toast.warning(title || 'Warning', toastOptions);
        break;
      case 'info':
        toast.info(title || 'Info', toastOptions);
        break;
    }
  }, []);

  const showAlert = useCallback((alert: Omit<NotificationAlert, 'id' | 'timestamp'>) => {
    const alertId = `alert-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const timestamp = new Date().toISOString();

    const fullAlert: NotificationAlert = {
      ...alert,
      id: alertId,
      timestamp,
    };

    // Show as toast notification
    const toastMessage = alert.device 
      ? `${alert.message} (Device: ${alert.device})`
      : alert.message;

    const toastOptions = {
      description: toastMessage,
      duration: alert.auto_dismiss ? 5000 : Infinity,
      action: alert.auto_dismiss ? undefined : {
        label: 'Dismiss',
        onClick: () => {},
      },
    };

    switch (alert.type) {
      case 'success':
        toast.success(alert.title, toastOptions);
        break;
      case 'error':
        toast.error(alert.title, toastOptions);
        break;
      case 'warning':
        toast.warning(alert.title, toastOptions);
        break;
      case 'info':
        toast.info(alert.title, toastOptions);
        break;
    }
  }, []);

  const dismissAlert = useCallback((id: string) => {
    toast.dismiss(id);
  }, []);

  // Handle incoming WebSocket alerts
  useEffect(() => {
    if (alertData) {
      try {
        const alert = alertData as NotificationAlert;
        showAlert({
          type: alert.type,
          title: alert.title,
          message: alert.message,
          device: alert.device,
          service: alert.service,
          auto_dismiss: alert.auto_dismiss ?? true,
        });
      } catch (error) {
        console.error('Failed to process incoming alert:', error);
      }
    }
  }, [alertData, showAlert]);

  const value: NotificationContextType = {
    showToast,
    showAlert,
    dismissAlert,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}
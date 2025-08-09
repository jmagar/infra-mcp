/**
 * Notification System
 * Toast notifications and user feedback system
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  CheckCircle, 
  AlertTriangle, 
  XCircle, 
  Info, 
  X, 
  Bell,
  AlertCircle 
} from 'lucide-react';
import { cn } from '@/lib/design-system';

// Notification types
export type NotificationType = 'success' | 'error' | 'warning' | 'info';

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message?: string;
  duration?: number; // in milliseconds, 0 = persistent
  action?: {
    label: string;
    onClick: () => void;
  };
  dismissible?: boolean;
  timestamp: number;
}

interface NotificationContextType {
  notifications: Notification[];
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => string;
  removeNotification: (id: string) => void;
  clearAllNotifications: () => void;
  success: (title: string, message?: string, options?: Partial<Notification>) => string;
  error: (title: string, message?: string, options?: Partial<Notification>) => string;
  warning: (title: string, message?: string, options?: Partial<Notification>) => string;
  info: (title: string, message?: string, options?: Partial<Notification>) => string;
}

const NotificationContext = createContext<NotificationContextType | null>(null);

// Default configuration
const DEFAULT_DURATIONS = {
  success: 4000,
  error: 8000,
  warning: 6000,
  info: 5000,
};

// Provider component
interface NotificationProviderProps {
  children: React.ReactNode;
  maxNotifications?: number;
}

export function NotificationProvider({ children, maxNotifications = 5 }: NotificationProviderProps) {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const addNotification = useCallback((notification: Omit<Notification, 'id' | 'timestamp'>) => {
    const id = `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const timestamp = Date.now();
    
    const newNotification: Notification = {
      ...notification,
      id,
      timestamp,
      duration: notification.duration ?? DEFAULT_DURATIONS[notification.type],
      dismissible: notification.dismissible ?? true,
    };

    setNotifications(prev => {
      // Add new notification and limit total count
      const updated = [newNotification, ...prev].slice(0, maxNotifications);
      return updated;
    });

    // Auto-remove after duration
    if (newNotification.duration && newNotification.duration > 0) {
      setTimeout(() => {
        removeNotification(id);
      }, newNotification.duration);
    }

    return id;
  }, [maxNotifications]);

  const removeNotification = useCallback((id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  }, []);

  const clearAllNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  // Convenience methods
  const success = useCallback((title: string, message?: string, options?: Partial<Notification>) => {
    return addNotification({ ...options, type: 'success', title, message });
  }, [addNotification]);

  const error = useCallback((title: string, message?: string, options?: Partial<Notification>) => {
    return addNotification({ ...options, type: 'error', title, message });
  }, [addNotification]);

  const warning = useCallback((title: string, message?: string, options?: Partial<Notification>) => {
    return addNotification({ ...options, type: 'warning', title, message });
  }, [addNotification]);

  const info = useCallback((title: string, message?: string, options?: Partial<Notification>) => {
    return addNotification({ ...options, type: 'info', title, message });
  }, [addNotification]);

  const value: NotificationContextType = {
    notifications,
    addNotification,
    removeNotification,
    clearAllNotifications,
    success,
    error,
    warning,
    info,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
      <NotificationContainer />
    </NotificationContext.Provider>
  );
}

// Hook to use notifications
export function useNotifications() {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
}

// Individual notification component
interface NotificationItemProps {
  notification: Notification;
  onDismiss: (id: string) => void;
}

function NotificationItem({ notification, onDismiss }: NotificationItemProps) {
  const [isRemoving, setIsRemoving] = useState(false);

  const handleDismiss = () => {
    setIsRemoving(true);
    setTimeout(() => onDismiss(notification.id), 150);
  };

  // Auto-dismiss timer indicator
  const [progress, setProgress] = useState(100);

  useEffect(() => {
    if (!notification.duration || notification.duration === 0) return;

    const interval = setInterval(() => {
      setProgress(prev => {
        const elapsed = Date.now() - notification.timestamp;
        const remaining = Math.max(0, notification.duration! - elapsed);
        return (remaining / notification.duration!) * 100;
      });
    }, 50);

    return () => clearInterval(interval);
  }, [notification]);

  const getNotificationStyles = () => {
    const base = "border-l-4 bg-background";
    
    switch (notification.type) {
      case 'success':
        return cn(base, "border-l-green-500 bg-green-50 dark:bg-green-950/20");
      case 'error':
        return cn(base, "border-l-red-500 bg-red-50 dark:bg-red-950/20");
      case 'warning':
        return cn(base, "border-l-yellow-500 bg-yellow-50 dark:bg-yellow-950/20");
      case 'info':
        return cn(base, "border-l-blue-500 bg-blue-50 dark:bg-blue-950/20");
      default:
        return base;
    }
  };

  const getIcon = () => {
    const iconProps = { className: "w-5 h-5" };
    
    switch (notification.type) {
      case 'success':
        return <CheckCircle {...iconProps} className="w-5 h-5 text-green-600" />;
      case 'error':
        return <XCircle {...iconProps} className="w-5 h-5 text-red-600" />;
      case 'warning':
        return <AlertTriangle {...iconProps} className="w-5 h-5 text-yellow-600" />;
      case 'info':
        return <Info {...iconProps} className="w-5 h-5 text-blue-600" />;
      default:
        return <Bell {...iconProps} />;
    }
  };

  return (
    <Card 
      className={cn(
        "mb-2 shadow-lg transition-all duration-300 overflow-hidden",
        getNotificationStyles(),
        isRemoving ? "opacity-0 transform translate-x-full" : "opacity-100 transform translate-x-0"
      )}
    >
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0">
            {getIcon()}
          </div>
          
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-semibold text-foreground">
              {notification.title}
            </h4>
            {notification.message && (
              <p className="text-sm text-muted-foreground mt-1">
                {notification.message}
              </p>
            )}
            
            {notification.action && (
              <Button 
                variant="link" 
                size="sm"
                className="p-0 h-auto mt-2 text-primary hover:text-primary/80"
                onClick={notification.action.onClick}
              >
                {notification.action.label}
              </Button>
            )}
          </div>

          {notification.dismissible && (
            <Button
              variant="ghost"
              size="sm"
              className="h-auto p-1 hover:bg-muted/50"
              onClick={handleDismiss}
            >
              <X className="w-4 h-4" />
            </Button>
          )}
        </div>

        {/* Progress indicator */}
        {notification.duration && notification.duration > 0 && (
          <div className="mt-3 h-1 bg-muted rounded-full overflow-hidden">
            <div 
              className={cn(
                "h-full transition-all duration-75 ease-linear",
                notification.type === 'success' && "bg-green-500",
                notification.type === 'error' && "bg-red-500",
                notification.type === 'warning' && "bg-yellow-500",
                notification.type === 'info' && "bg-blue-500"
              )}
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Container component for notifications
function NotificationContainer() {
  const { notifications, removeNotification, clearAllNotifications } = useNotifications();

  if (notifications.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 w-80 max-w-[calc(100vw-2rem)]">
      <div className="space-y-2">
        {notifications.length > 3 && (
          <div className="flex justify-between items-center p-2 bg-background border rounded-lg mb-2">
            <span className="text-sm text-muted-foreground">
              {notifications.length} notifications
            </span>
            <Button 
              variant="ghost" 
              size="sm"
              onClick={clearAllNotifications}
              className="text-xs"
            >
              Clear all
            </Button>
          </div>
        )}
        
        {notifications.slice(0, 5).map(notification => (
          <NotificationItem
            key={notification.id}
            notification={notification}
            onDismiss={removeNotification}
          />
        ))}
      </div>
    </div>
  );
}

// Inline notification component (for forms, etc.)
interface InlineNotificationProps {
  type: NotificationType;
  title: string;
  message?: string;
  onDismiss?: () => void;
  className?: string;
}

export function InlineNotification({ 
  type, 
  title, 
  message, 
  onDismiss, 
  className 
}: InlineNotificationProps) {
  const getStyles = () => {
    switch (type) {
      case 'success':
        return "border-green-200 bg-green-50 text-green-800 dark:border-green-800 dark:bg-green-950 dark:text-green-200";
      case 'error':
        return "border-red-200 bg-red-50 text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200";
      case 'warning':
        return "border-yellow-200 bg-yellow-50 text-yellow-800 dark:border-yellow-800 dark:bg-yellow-950 dark:text-yellow-200";
      case 'info':
        return "border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-200";
      default:
        return "border-muted bg-muted/50 text-foreground";
    }
  };

  const getIcon = () => {
    switch (type) {
      case 'success':
        return <CheckCircle className="w-4 h-4" />;
      case 'error':
        return <AlertCircle className="w-4 h-4" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4" />;
      case 'info':
        return <Info className="w-4 h-4" />;
    }
  };

  return (
    <div className={cn(
      "flex items-start gap-3 p-3 rounded-lg border",
      getStyles(),
      className
    )}>
      {getIcon()}
      <div className="flex-1">
        <h5 className="font-medium text-sm">{title}</h5>
        {message && <p className="text-sm mt-1 opacity-90">{message}</p>}
      </div>
      {onDismiss && (
        <Button variant="ghost" size="sm" onClick={onDismiss} className="h-auto p-1">
          <X className="w-3 h-3" />
        </Button>
      )}
    </div>
  );
}
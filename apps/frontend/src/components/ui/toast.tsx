import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { X, CheckCircle, AlertTriangle, Info, XCircle } from 'lucide-react';
import { cn } from '@/lib/design-system';

const toastVariants = cva(
  [
    "group pointer-events-auto relative flex w-full items-center justify-between space-x-2 overflow-hidden rounded-md border p-4 shadow-lg transition-all",
    "data-[swipe=cancel]:translate-x-0 data-[swipe=end]:translate-x-[var(--radix-toast-swipe-end-x)] data-[swipe=move]:translate-x-[var(--radix-toast-swipe-move-x)] data-[swipe=move]:transition-none",
    "data-[state=open]:animate-in data-[state=open]:slide-in-from-right-full data-[state=open]:fade-in",
    "data-[state=closed]:animate-out data-[state=closed]:fade-out-80 data-[state=closed]:slide-out-to-right-full",
    "glass-ultra hover:glass-tinted backdrop-blur-md",
    "border-border/50 shadow-xl shadow-background/20",
    "hover:scale-[1.02] hover-lift",
    "animate-slide-in-right animate-fade-in"
  ],
  {
    variants: {
      variant: {
        default: "bg-background text-foreground border-border",
        success: [
          "border-green-500/20 bg-green-50/80 dark:bg-green-950/80 text-green-900 dark:text-green-100",
          "shadow-green-500/20"
        ],
        error: [
          "border-red-500/20 bg-red-50/80 dark:bg-red-950/80 text-red-900 dark:text-red-100",
          "shadow-red-500/20"
        ],
        warning: [
          "border-yellow-500/20 bg-yellow-50/80 dark:bg-yellow-950/80 text-yellow-900 dark:text-yellow-100",
          "shadow-yellow-500/20"
        ],
        info: [
          "border-blue-500/20 bg-blue-50/80 dark:bg-blue-950/80 text-blue-900 dark:text-blue-100",
          "shadow-blue-500/20"
        ],
      },
      size: {
        sm: "text-sm px-3 py-2",
        default: "text-sm px-4 py-3",
        lg: "text-base px-6 py-4",
      }
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

interface Toast {
  id: string;
  title?: string;
  description?: string;
  action?: React.ReactNode;
  variant?: VariantProps<typeof toastVariants>['variant'];
  size?: VariantProps<typeof toastVariants>['size'];
  duration?: number;
  dismissible?: boolean;
  persistent?: boolean;
  onDismiss?: () => void;
}

interface ToastContextValue {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => string;
  removeToast: (id: string) => void;
  removeAll: () => void;
}

const ToastContext = React.createContext<ToastContextValue | undefined>(undefined);

export function useToast() {
  const context = React.useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

export interface ToastProviderProps {
  children: React.ReactNode;
  maxToasts?: number;
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center';
  defaultDuration?: number;
}

export function ToastProvider({ 
  children, 
  maxToasts = 5,
  position = 'top-right',
  defaultDuration = 5000 
}: ToastProviderProps) {
  const [toasts, setToasts] = React.useState<Toast[]>([]);

  const addToast = React.useCallback((toast: Omit<Toast, 'id'>) => {
    const id = Math.random().toString(36).substring(2, 9);
    const newToast: Toast = {
      ...toast,
      id,
      duration: toast.duration ?? defaultDuration,
      dismissible: toast.dismissible ?? true,
    };

    setToasts(current => {
      const updated = [newToast, ...current.slice(0, maxToasts - 1)];
      return updated;
    });

    // Auto dismiss after duration
    if (!newToast.persistent && newToast.duration && newToast.duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, newToast.duration);
    }

    return id;
  }, [maxToasts, defaultDuration]);

  const removeToast = React.useCallback((id: string) => {
    setToasts(current => current.filter(toast => toast.id !== id));
  }, []);

  const removeAll = React.useCallback(() => {
    setToasts([]);
  }, []);

  const contextValue = React.useMemo(() => ({
    toasts,
    addToast,
    removeToast,
    removeAll,
  }), [toasts, addToast, removeToast, removeAll]);

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      <ToastViewport position={position} toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  );
}

interface ToastViewportProps {
  toasts: Toast[];
  position: ToastProviderProps['position'];
  onRemove: (id: string) => void;
}

function ToastViewport({ toasts, position = 'top-right', onRemove }: ToastViewportProps) {
  const getPositionClasses = () => {
    switch (position) {
      case 'top-left':
        return 'top-0 left-0';
      case 'top-right':
        return 'top-0 right-0';
      case 'top-center':
        return 'top-0 left-1/2 -translate-x-1/2';
      case 'bottom-left':
        return 'bottom-0 left-0';
      case 'bottom-right':
        return 'bottom-0 right-0';
      case 'bottom-center':
        return 'bottom-0 left-1/2 -translate-x-1/2';
      default:
        return 'top-0 right-0';
    }
  };

  if (toasts.length === 0) return null;

  return (
    <div
      className={cn(
        "fixed z-[100] flex max-h-screen w-full flex-col-reverse p-4 sm:max-w-[420px]",
        getPositionClasses()
      )}
    >
      {toasts.map((toast, index) => (
        <ToastComponent
          key={toast.id}
          toast={toast}
          onRemove={onRemove}
          style={{
            animationDelay: `${index * 100}ms`,
            zIndex: 100 - index,
          }}
        />
      ))}
    </div>
  );
}

interface ToastComponentProps {
  toast: Toast;
  onRemove: (id: string) => void;
  style?: React.CSSProperties;
}

function ToastComponent({ toast, onRemove, style }: ToastComponentProps) {
  const [isVisible, setIsVisible] = React.useState(true);
  const [progress, setProgress] = React.useState(100);

  React.useEffect(() => {
    if (!toast.persistent && toast.duration && toast.duration > 0) {
      const startTime = Date.now();
      const timer = setInterval(() => {
        const elapsed = Date.now() - startTime;
        const remaining = Math.max(0, toast.duration! - elapsed);
        const progressPercent = (remaining / toast.duration!) * 100;
        setProgress(progressPercent);

        if (remaining <= 0) {
          clearInterval(timer);
        }
      }, 100);

      return () => clearInterval(timer);
    }
  }, [toast.duration, toast.persistent]);

  const handleDismiss = () => {
    if (!toast.dismissible) return;
    
    setIsVisible(false);
    toast.onDismiss?.();
    
    // Delay removal to allow exit animation
    setTimeout(() => {
      onRemove(toast.id);
    }, 150);
  };

  const getIcon = () => {
    switch (toast.variant) {
      case 'success':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'error':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'warning':
        return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
      case 'info':
        return <Info className="h-5 w-5 text-blue-500" />;
      default:
        return null;
    }
  };

  const icon = getIcon();

  return (
    <div
      className={cn(
        toastVariants({ variant: toast.variant, size: toast.size }),
        !isVisible && "animate-fade-out animate-slide-out-to-right",
        "mb-2 last:mb-0"
      )}
      style={style}
    >
      <div className="flex items-start gap-3 flex-1">
        {icon && (
          <div className="flex-shrink-0 pt-0.5">
            {icon}
          </div>
        )}
        <div className="flex-1 space-y-1">
          {toast.title && (
            <div className="font-medium leading-none">
              {toast.title}
            </div>
          )}
          {toast.description && (
            <div className="text-sm opacity-90 leading-relaxed">
              {toast.description}
            </div>
          )}
        </div>
      </div>

      {toast.action && (
        <div className="flex-shrink-0">
          {toast.action}
        </div>
      )}

      {toast.dismissible && (
        <button
          onClick={handleDismiss}
          className={cn(
            "ml-2 flex-shrink-0 rounded-full p-1.5 opacity-70 hover:opacity-100 transition-all duration-200",
            "hover:bg-background/20 hover:scale-110 active:scale-95"
          )}
        >
          <X className="h-4 w-4" />
        </button>
      )}

      {/* Progress bar */}
      {!toast.persistent && toast.duration && toast.duration > 0 && (
        <div className="absolute bottom-0 left-0 right-0 h-1 bg-background/20 overflow-hidden rounded-b-md">
          <div
            className={cn(
              "h-full transition-all duration-100 ease-linear",
              toast.variant === 'success' && "bg-green-500",
              toast.variant === 'error' && "bg-red-500",
              toast.variant === 'warning' && "bg-yellow-500",
              toast.variant === 'info' && "bg-blue-500",
              !toast.variant && "bg-primary"
            )}
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </div>
  );
}

// Convenience functions for common toast types
export const toast = {
  success: (message: string, options?: Partial<Omit<Toast, 'id' | 'variant'>>) => {
    const { addToast } = useToastUnsafe();
    return addToast({
      title: 'Success',
      description: message,
      variant: 'success',
      ...options,
    });
  },
  
  error: (message: string, options?: Partial<Omit<Toast, 'id' | 'variant'>>) => {
    const { addToast } = useToastUnsafe();
    return addToast({
      title: 'Error',
      description: message,
      variant: 'error',
      duration: 7000, // Longer duration for errors
      ...options,
    });
  },
  
  warning: (message: string, options?: Partial<Omit<Toast, 'id' | 'variant'>>) => {
    const { addToast } = useToastUnsafe();
    return addToast({
      title: 'Warning',
      description: message,
      variant: 'warning',
      duration: 6000,
      ...options,
    });
  },
  
  info: (message: string, options?: Partial<Omit<Toast, 'id' | 'variant'>>) => {
    const { addToast } = useToastUnsafe();
    return addToast({
      title: 'Info',
      description: message,
      variant: 'info',
      ...options,
    });
  },
  
  custom: (toast: Omit<Toast, 'id'>) => {
    const { addToast } = useToastUnsafe();
    return addToast(toast);
  },
};

// Unsafe version that doesn't throw if used outside provider (for convenience functions)
function useToastUnsafe() {
  return React.useContext(ToastContext) || {
    toasts: [],
    addToast: () => '',
    removeToast: () => {},
    removeAll: () => {},
  };
}
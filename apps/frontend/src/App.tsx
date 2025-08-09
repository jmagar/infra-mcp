import { RouterProvider } from 'react-router-dom';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { NotificationProvider, ErrorBoundary } from '@/components/common';
import { router } from './router';
import { Toaster } from '@/components/ui/sonner';
import './App.css';

function App() {
  return (
    <ErrorBoundary onError={(error, errorInfo) => {
      // TODO: Log to external error tracking service
      console.error('App-level error:', error, errorInfo);
    }}>
      <ThemeProvider defaultTheme="system" storageKey="infrastructor-theme">
        <NotificationProvider maxNotifications={5}>
          <RouterProvider router={router} />
          {/* Keep Sonner as fallback for existing toast usage */}
          <Toaster position="bottom-right" expand={false} richColors={true} closeButton={true} />
        </NotificationProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
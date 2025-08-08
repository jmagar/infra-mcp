import { RouterProvider } from 'react-router-dom';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { NotificationProvider } from '@/contexts/NotificationContext';
import { router } from './router';
import { Toaster } from '@/components/ui/sonner';
import './App.css';

function App() {
  return (
    <ThemeProvider defaultTheme="system" storageKey="infrastructor-theme">
      <NotificationProvider>
        <RouterProvider router={router} />
        <Toaster position="top-right" expand={true} richColors={true} closeButton={true} />
      </NotificationProvider>
    </ThemeProvider>
  );
}

export default App;
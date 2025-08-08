import { createBrowserRouter } from 'react-router-dom';
import { AppLayout } from './components/layouts/AppLayout';
import { Dashboard } from './pages/Dashboard';

export const testRouter = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: <Dashboard />,
      },
    ],
  },
]);
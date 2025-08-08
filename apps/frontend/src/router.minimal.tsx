import { createBrowserRouter } from 'react-router-dom';
import { AppLayout } from './components/layouts/AppLayout';

function TestPage() {
  return (
    <div style={{ padding: '20px' }}>
      <h1>Testing NotificationProvider</h1>
      <p>If you see this page with the sidebar, NotificationProvider is working.</p>
    </div>
  );
}

export const minimalRouter = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: <TestPage />,
      },
    ],
  },
]);
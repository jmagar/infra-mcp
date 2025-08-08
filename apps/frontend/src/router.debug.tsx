import { createBrowserRouter } from 'react-router-dom';
import { AppLayout } from './components/layouts/AppLayout';

// Test each page component one by one to find the broken one
function TestComponent() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Testing Individual Components</h1>
      <div className="space-y-4">
        <div className="border p-4 rounded">
          <h2 className="font-semibold">Testing Dashboard import...</h2>
          <TestDashboard />
        </div>
      </div>
    </div>
  );
}

function TestDashboard() {
  try {
    // Try importing Dashboard
    const { Dashboard } = require('./pages/Dashboard');
    return <div>✅ Dashboard import successful</div>;
  } catch (error) {
    return <div className="text-red-500">❌ Dashboard import failed: {String(error)}</div>;
  }
}

export const debugRouter = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: <TestComponent />,
      },
    ],
  },
]);
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppLayout } from './components/layouts/AppLayout';
import { Dashboard } from './pages/Dashboard';
import { InfrastructureDashboard } from './pages/InfrastructureDashboard';
import { DeviceList } from './pages/devices/DeviceList';
import { DeviceDetails } from './pages/devices/DeviceDetails';
import { ContainerList } from './pages/containers/ContainerList';
import { ContainerDetails } from './pages/containers/ContainerDetails';
import { StorageOverview } from './pages/storage/StorageOverview';
import { ZFSPools } from './pages/storage/ZFSPools';
import { ZFSDatasets } from './pages/storage/ZFSDatasets';
import { ZFSSnapshots } from './pages/storage/ZFSSnapshots';
import { DriveHealth } from './pages/storage/DriveHealth';
import { NetworkOverview } from './pages/networking/NetworkOverview';
import { ProxyConfigs } from './pages/networking/ProxyConfigs';
import { Deployments } from './pages/deployments/Deployments';
import { Monitoring } from './pages/monitoring/Monitoring';
import { SystemOverview } from './pages/system/SystemOverview';
import { Updates } from './pages/system/Updates';
import { Backups } from './pages/system/Backups';
import { VMs } from './pages/system/VMs';
import { Settings } from './pages/Settings';
import { NotificationDemo } from './pages/notifications/NotificationDemo';
import { ErrorBoundary } from './components/common/ErrorBoundary';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    errorElement: <ErrorBoundary><div>Something went wrong</div></ErrorBoundary>,
    children: [
      // Default route - redirect to new dashboard
      {
        index: true,
        element: <InfrastructureDashboard />,
      },
      
      // Dashboard routes
      {
        path: 'dashboard',
        element: <InfrastructureDashboard />,
      },
      {
        path: 'dashboard-old',
        element: <Dashboard />,
      },
      
      // Device Management
      {
        path: 'devices',
        children: [
          {
            index: true,
            element: <DeviceList />,
          },
          {
            path: ':hostname',
            element: <DeviceDetails />,
          },
        ],
      },
      
      // Container Management
      {
        path: 'containers',
        children: [
          {
            index: true,
            element: <ContainerList />,
          },
          {
            path: ':device/:containerName',
            element: <ContainerDetails />,
          },
        ],
      },
      
      // Storage Management
      {
        path: 'storage',
        element: <StorageOverview />,
        children: [
          {
            index: true,
            element: <Navigate to="pools" replace />,
          },
          {
            path: 'pools',
            element: <ZFSPools />,
          },
          {
            path: 'datasets',
            element: <ZFSDatasets />,
          },
          {
            path: 'snapshots',
            element: <ZFSSnapshots />,
          },
          {
            path: 'drives',
            element: <DriveHealth />,
          },
        ],
      },
      
      // Networking
      {
        path: 'networking',
        element: <NetworkOverview />,
        children: [
          {
            index: true,
            element: <Navigate to="proxy" replace />,
          },
          {
            path: 'proxy',
            element: <ProxyConfigs />,
          },
        ],
      },
      
      // Deployments
      {
        path: 'deployments',
        element: <Deployments />,
      },
      
      // Monitoring
      {
        path: 'monitoring',
        element: <Monitoring />,
      },
      
      // System Management
      {
        path: 'system',
        element: <SystemOverview />,
        children: [
          {
            index: true,
            element: <Navigate to="updates" replace />,
          },
          {
            path: 'updates',
            element: <Updates />,
          },
          {
            path: 'backups',
            element: <Backups />,
          },
          {
            path: 'vms',
            element: <VMs />,
          },
        ],
      },
      
      // Settings
      {
        path: 'settings',
        element: <Settings />,
      },
      
      // Notification Demo (development only)
      {
        path: 'notifications-demo',
        element: <NotificationDemo />,
      },
      
      // Catch all - redirect to dashboard
      {
        path: '*',
        element: <Navigate to="/" replace />,
      },
    ],
  },
]);
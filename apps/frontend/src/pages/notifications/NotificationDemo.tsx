import { useState } from 'react';
import { useNotifications } from '@/contexts/NotificationContext';
import { useNotificationEvents } from '@/hooks/useNotificationEvents';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import {
  Bell as BellIcon,
  CheckCircle as CheckCircleIcon,
  AlertTriangle as ExclamationTriangleIcon,
  Info as InformationCircleIcon,
  XCircle as XCircleIcon,
} from 'lucide-react';

export function NotificationDemo() {
  const { showToast, showAlert } = useNotifications();
  const {
    notifyContainerAction,
    notifyDeviceStatus,
    notifyResourceAlert,
    notifyServiceStatus,
    notifyZFSStatus,
    notifyDeployment,
    notifyError,
    notifySuccess,
  } = useNotificationEvents();

  const [customMessage, setCustomMessage] = useState('');
  const [customTitle, setCustomTitle] = useState('');
  const [customType, setCustomType] = useState<'success' | 'error' | 'warning' | 'info'>('info');

  const showCustomToast = () => {
    if (!customMessage) return;
    showToast(customType, customMessage, customTitle || undefined);
    setCustomMessage('');
    setCustomTitle('');
  };

  const showCustomAlert = () => {
    if (!customMessage) return;
    showAlert({
      type: customType,
      title: customTitle || 'Custom Alert',
      message: customMessage,
      device: 'demo-server',
      auto_dismiss: customType === 'success' || customType === 'info',
    });
    setCustomMessage('');
    setCustomTitle('');
  };

  const demoNotifications = [
    {
      category: 'Container Actions',
      items: [
        {
          title: 'Container Started',
          action: () => notifyContainerAction('start', 'nginx', 'server-01', true),
        },
        {
          title: 'Container Failed to Stop',
          action: () => notifyContainerAction('stop', 'database', 'server-02', false, 'Permission denied'),
        },
        {
          title: 'Container Restarted',
          action: () => notifyContainerAction('restart', 'redis', 'server-03', true),
        },
      ],
    },
    {
      category: 'Device Status',
      items: [
        {
          title: 'Device Online',
          action: () => notifyDeviceStatus('server-04', 'online', 'Connection restored'),
        },
        {
          title: 'Device Offline',
          action: () => notifyDeviceStatus('server-05', 'offline', 'Network timeout'),
        },
        {
          title: 'Device Error',
          action: () => notifyDeviceStatus('server-06', 'error', 'SSH connection failed'),
        },
      ],
    },
    {
      category: 'Resource Alerts',
      items: [
        {
          title: 'High CPU Usage',
          action: () => notifyResourceAlert('server-07', 'cpu', 'warning', 89.5),
        },
        {
          title: 'Critical Memory Usage',
          action: () => notifyResourceAlert('server-08', 'memory', 'critical', 95.2),
        },
        {
          title: 'Disk Space Warning',
          action: () => notifyResourceAlert('server-09', 'disk', 'warning', 82.1),
        },
      ],
    },
    {
      category: 'Service Health',
      items: [
        {
          title: 'Service Healthy',
          action: () => notifyServiceStatus('postgresql', 'healthy', 'db-server'),
        },
        {
          title: 'Service Unhealthy',
          action: () => notifyServiceStatus('elasticsearch', 'unhealthy', 'search-server', 'Health check failed'),
        },
        {
          title: 'Service Degraded',
          action: () => notifyServiceStatus('redis', 'degraded', 'cache-server', 'High response times'),
        },
      ],
    },
    {
      category: 'ZFS Status',
      items: [
        {
          title: 'ZFS Pool Healthy',
          action: () => notifyZFSStatus('tank', 'healthy', 'storage-01'),
        },
        {
          title: 'ZFS Pool Degraded',
          action: () => notifyZFSStatus('backup', 'degraded', 'storage-02', 'One drive failed'),
        },
        {
          title: 'ZFS Pool Faulted',
          action: () => notifyZFSStatus('archive', 'faulted', 'storage-03', 'Multiple drive failures'),
        },
      ],
    },
    {
      category: 'Deployments',
      items: [
        {
          title: 'Deployment Started',
          action: () => notifyDeployment('web-app', 'started', 'app-server'),
        },
        {
          title: 'Deployment Complete',
          action: () => notifyDeployment('api-service', 'completed', 'api-server'),
        },
        {
          title: 'Deployment Failed',
          action: () => notifyDeployment('background-worker', 'failed', 'worker-server', 'Build failed'),
        },
      ],
    },
  ];

  const getTypeIcon = (type: string) => {
    const iconClass = "h-4 w-4";
    switch (type) {
      case 'success':
        return <CheckCircleIcon className={`${iconClass} text-green-500`} />;
      case 'warning':
        return <ExclamationTriangleIcon className={`${iconClass} text-yellow-500`} />;
      case 'error':
        return <XCircleIcon className={`${iconClass} text-red-500`} />;
      default:
        return <InformationCircleIcon className={`${iconClass} text-blue-500`} />;
    }
  };

  return (
    <div className="p-6 space-y-8">
      <div className="flex items-center space-x-3">
        <BellIcon className="h-8 w-8 text-blue-500" />
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
            Notification System Demo
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Test toast messages and real-time alerts
          </p>
        </div>
      </div>

      {/* Custom Notification Form */}
      <Card>
        <CardHeader>
          <CardTitle>Custom Notification</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Title (Optional)</label>
              <Input
                placeholder="Notification title..."
                value={customTitle}
                onChange={(e) => setCustomTitle(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Type</label>
              <Select value={customType} onValueChange={setCustomType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="info">
                    <div className="flex items-center space-x-2">
                      <InformationCircleIcon className="h-4 w-4 text-blue-500" />
                      <span>Info</span>
                    </div>
                  </SelectItem>
                  <SelectItem value="success">
                    <div className="flex items-center space-x-2">
                      <CheckCircleIcon className="h-4 w-4 text-green-500" />
                      <span>Success</span>
                    </div>
                  </SelectItem>
                  <SelectItem value="warning">
                    <div className="flex items-center space-x-2">
                      <ExclamationTriangleIcon className="h-4 w-4 text-yellow-500" />
                      <span>Warning</span>
                    </div>
                  </SelectItem>
                  <SelectItem value="error">
                    <div className="flex items-center space-x-2">
                      <XCircleIcon className="h-4 w-4 text-red-500" />
                      <span>Error</span>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Message *</label>
            <Input
              placeholder="Notification message..."
              value={customMessage}
              onChange={(e) => setCustomMessage(e.target.value)}
            />
          </div>
          <div className="flex space-x-2">
            <Button onClick={showCustomToast} disabled={!customMessage}>
              Show Toast
            </Button>
            <Button onClick={showCustomAlert} variant="outline" disabled={!customMessage}>
              Show Alert
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Demo Categories */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {demoNotifications.map((category) => (
          <Card key={category.category}>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <span>{category.category}</span>
                <Badge variant="secondary">{category.items.length}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {category.items.map((item) => (
                  <Button
                    key={item.title}
                    variant="outline"
                    onClick={item.action}
                    className="w-full justify-start"
                  >
                    {item.title}
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Usage Information */}
      <Card>
        <CardHeader>
          <CardTitle>Usage Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h4 className="font-medium mb-2">Toast Messages</h4>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
              Toast messages appear in the top-right corner and automatically dismiss after a few seconds.
            </p>
            <ul className="text-sm text-gray-600 dark:text-gray-400 list-disc list-inside space-y-1">
              <li>Success and Info: 4 seconds</li>
              <li>Error: 6 seconds</li>
              <li>All toasts have a close button</li>
            </ul>
          </div>
          <div>
            <h4 className="font-medium mb-2">Alert Notifications</h4>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
              Alert notifications appear in the notification center (bell icon in header).
            </p>
            <ul className="text-sm text-gray-600 dark:text-gray-400 list-disc list-inside space-y-1">
              <li>Persistent alerts require manual dismissal</li>
              <li>Auto-dismiss alerts disappear after 5 seconds</li>
              <li>Unread count shows in notification bell</li>
              <li>Include device and service context</li>
            </ul>
          </div>
          <div>
            <h4 className="font-medium mb-2">Real-time Integration</h4>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              In production, notifications are triggered by:
            </p>
            <ul className="text-sm text-gray-600 dark:text-gray-400 list-disc list-inside space-y-1">
              <li>WebSocket messages from the backend</li>
              <li>API operation results (container actions, deployments)</li>
              <li>System monitoring alerts (CPU, memory, disk usage)</li>
              <li>Service health checks</li>
              <li>ZFS pool status changes</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
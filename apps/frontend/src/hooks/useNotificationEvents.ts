import { useEffect } from 'react';
import { useNotifications } from '@/contexts/NotificationContext';

interface NotificationEventConfig {
  device?: string;
  container?: string;
  service?: string;
}

export function useNotificationEvents(config: NotificationEventConfig = {}) {
  const { showToast, showAlert } = useNotifications();

  // Container lifecycle notifications
  const notifyContainerAction = (
    action: 'start' | 'stop' | 'restart' | 'remove',
    containerName: string,
    device: string,
    success: boolean = true,
    error?: string
  ) => {
    const actionPast = {
      start: 'started',
      stop: 'stopped',
      restart: 'restarted',
      remove: 'removed',
    }[action];

    if (success) {
      showToast(
        'success',
        `Container "${containerName}" has been ${actionPast} successfully`,
        'Container Action Complete'
      );
    } else {
      showToast(
        'error',
        error || `Failed to ${action} container "${containerName}"`,
        'Container Action Failed'
      );
    }
  };

  // Device connectivity notifications
  const notifyDeviceStatus = (
    device: string,
    status: 'online' | 'offline' | 'error',
    message?: string
  ) => {
    const config = {
      online: { type: 'success' as const, title: 'Device Online' },
      offline: { type: 'warning' as const, title: 'Device Offline' },
      error: { type: 'error' as const, title: 'Device Error' },
    }[status];

    showAlert({
      type: config.type,
      title: config.title,
      message: message || `Device "${device}" is now ${status}`,
      device,
      auto_dismiss: status === 'online',
    });
  };

  // System resource alerts
  const notifyResourceAlert = (
    device: string,
    resource: 'cpu' | 'memory' | 'disk',
    level: 'warning' | 'critical',
    usage: number
  ) => {
    const resourceNames = {
      cpu: 'CPU',
      memory: 'Memory',
      disk: 'Disk',
    };

    showAlert({
      type: level === 'critical' ? 'error' : 'warning',
      title: `${resourceNames[resource]} Usage ${level === 'critical' ? 'Critical' : 'High'}`,
      message: `${resourceNames[resource]} usage is at ${usage.toFixed(1)}% on device "${device}"`,
      device,
      auto_dismiss: false,
    });
  };

  // Service status notifications
  const notifyServiceStatus = (
    service: string,
    status: 'healthy' | 'unhealthy' | 'degraded',
    device?: string,
    details?: string
  ) => {
    const config = {
      healthy: { type: 'success' as const, title: 'Service Healthy' },
      unhealthy: { type: 'error' as const, title: 'Service Unhealthy' },
      degraded: { type: 'warning' as const, title: 'Service Degraded' },
    }[status];

    showAlert({
      type: config.type,
      title: config.title,
      message: details || `Service "${service}" is ${status}${device ? ` on device "${device}"` : ''}`,
      device,
      service,
      auto_dismiss: status === 'healthy',
    });
  };

  // ZFS health notifications
  const notifyZFSStatus = (
    pool: string,
    status: 'healthy' | 'degraded' | 'faulted',
    device: string,
    details?: string
  ) => {
    const config = {
      healthy: { type: 'success' as const, title: 'ZFS Pool Healthy' },
      degraded: { type: 'warning' as const, title: 'ZFS Pool Degraded' },
      faulted: { type: 'error' as const, title: 'ZFS Pool Faulted' },
    }[status];

    showAlert({
      type: config.type,
      title: config.title,
      message: details || `ZFS pool "${pool}" is ${status} on device "${device}"`,
      device,
      auto_dismiss: status === 'healthy',
    });
  };

  // Deployment notifications
  const notifyDeployment = (
    service: string,
    status: 'started' | 'completed' | 'failed',
    device: string,
    error?: string
  ) => {
    const config = {
      started: { type: 'info' as const, title: 'Deployment Started' },
      completed: { type: 'success' as const, title: 'Deployment Complete' },
      failed: { type: 'error' as const, title: 'Deployment Failed' },
    }[status];

    showToast(
      config.type,
      error || `Deployment of "${service}" ${status} on device "${device}"`,
      config.title
    );
  };

  // Generic error notifications
  const notifyError = (
    title: string,
    message: string,
    device?: string,
    persistent: boolean = false
  ) => {
    if (persistent) {
      showAlert({
        type: 'error',
        title,
        message,
        device,
        auto_dismiss: false,
      });
    } else {
      showToast('error', message, title);
    }
  };

  // Generic success notifications
  const notifySuccess = (
    title: string,
    message: string,
    device?: string
  ) => {
    showToast('success', message, title);
  };

  return {
    notifyContainerAction,
    notifyDeviceStatus,
    notifyResourceAlert,
    notifyServiceStatus,
    notifyZFSStatus,
    notifyDeployment,
    notifyError,
    notifySuccess,
  };
}
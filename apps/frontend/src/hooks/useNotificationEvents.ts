import { useEffect } from 'react';
import { useNotifications } from '@/components/common';

interface NotificationEventConfig {
  device?: string;
  container?: string;
  service?: string;
}

export function useNotificationEvents(config: NotificationEventConfig = {}) {
  const { success, error, warning, info } = useNotifications();

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
      success(
        'Container Action Complete',
        `Container "${containerName}" has been ${actionPast} successfully`
      );
    } else {
      error(
        'Container Action Failed',
        error || `Failed to ${action} container "${containerName}"`
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

    const notificationFn = config.type === 'success' ? success : 
                         config.type === 'warning' ? warning : error;
    
    notificationFn(
      config.title,
      message || `Device "${device}" is now ${status}`
    );
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

    const notificationFn = level === 'critical' ? error : warning;
    
    notificationFn(
      `${resourceNames[resource]} Usage ${level === 'critical' ? 'Critical' : 'High'}`,
      `${resourceNames[resource]} usage is at ${usage.toFixed(1)}% on device "${device}"`
    );
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

    const notificationFn = config.type === 'success' ? success : 
                         config.type === 'warning' ? warning : error;
    
    notificationFn(
      config.title,
      details || `Service "${service}" is ${status}${device ? ` on device "${device}"` : ''}`
    );
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

    const notificationFn = config.type === 'success' ? success : 
                         config.type === 'warning' ? warning : error;
    
    notificationFn(
      config.title,
      details || `ZFS pool "${pool}" is ${status} on device "${device}"`
    );
  };

  // Compose stack notifications
  const notifyComposeAction = (
    action: 'deploy' | 'stop' | 'restart' | 'remove' | 'modify',
    stackName: string,
    device: string,
    success: boolean = true,
    error?: string
  ) => {
    const actionPast = {
      deploy: 'deployed',
      stop: 'stopped',
      restart: 'restarted',
      remove: 'removed',
      modify: 'modified',
    }[action];

    if (success) {
      success(
        'Compose Action Complete',
        `Stack "${stackName}" has been ${actionPast} successfully`
      );
    } else {
      error(
        'Compose Action Failed',
        error || `Failed to ${action} stack "${stackName}"`
      );
    }
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

    const notificationFn = config.type === 'success' ? success : 
                         config.type === 'info' ? info : error;
    
    notificationFn(
      config.title,
      error || `Deployment of "${service}" ${status} on device "${device}"`
    );
  };

  // Generic error notifications
  const notifyError = (
    title: string,
    message: string,
    device?: string,
    persistent: boolean = false
  ) => {
    // Use error notification for both persistent and non-persistent
    error(title, message);
  };

  // Generic success notifications
  const notifySuccess = (
    title: string,
    message: string,
    device?: string
  ) => {
    success(title, message);
  };

  return {
    notifyContainerAction,
    notifyComposeAction,
    notifyDeviceStatus,
    notifyResourceAlert,
    notifyServiceStatus,
    notifyZFSStatus,
    notifyDeployment,
    notifyError,
    notifySuccess,
  };
}
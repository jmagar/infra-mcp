import { useEffect, useState } from 'react';
import { containerService } from '@/services';
import { useContainerStore } from '@/store/containerStore';
import { useUIStore } from '@/store/uiStore';
import type { 
  ContainerList, 
  ContainerResponse
} from '@infrastructor/shared-types';

export function useContainers(deviceHostname?: string) {
  const { 
    containers, 
    loading, 
    error, 
    setContainers, 
    setLoading, 
    setError,
    addContainer,
    updateContainer,
  } = useContainerStore();
  
  const { addNotification } = useUIStore();

  const fetchContainers = async (hostname?: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const containerList = hostname 
        ? await containerService.getByDevice(hostname)
        : await containerService.list();
      setContainers(containerList.items || []);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      setError(errorMessage);
      addNotification({
        type: 'error',
        title: 'Network error',
        message: 'Failed to connect to the server',
      });
    } finally {
      setLoading(false);
    }
  };

  const startContainer = async (deviceHostname: string, containerName: string): Promise<boolean> => {
    try {
      const result = await containerService.start(deviceHostname, containerName);
      
      if (result.success) {
        await fetchContainers(deviceHostname);
        addNotification({
          type: 'success',
          title: 'Container started',
          message: `Container ${containerName} has been started`,
        });
        return true;
      } else {
        addNotification({
          type: 'error',
          title: 'Failed to start container',
          message: result.message || 'Container start failed',
        });
        return false;
      }
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Error starting container',
        message: error instanceof Error ? error.message : 'Unknown error occurred',
      });
      return false;
    }
  };

  const stopContainer = async (deviceHostname: string, containerName: string): Promise<boolean> => {
    try {
      const result = await containerService.stop(deviceHostname, containerName);
      
      if (result.success) {
        await fetchContainers(deviceHostname);
        addNotification({
          type: 'success',
          title: 'Container stopped',
          message: `Container ${containerName} has been stopped`,
        });
        return true;
      } else {
        addNotification({
          type: 'error',
          title: 'Failed to stop container',
          message: result.message || 'Container stop failed',
        });
        return false;
      }
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Error stopping container',
        message: error instanceof Error ? error.message : 'Unknown error occurred',
      });
      return false;
    }
  };

  const restartContainer = async (deviceHostname: string, containerName: string): Promise<boolean> => {
    try {
      const result = await containerService.restart(deviceHostname, containerName);
      
      if (result.success) {
        await fetchContainers(deviceHostname);
        addNotification({
          type: 'success',
          title: 'Container restarted',
          message: `Container ${containerName} has been restarted`,
        });
        return true;
      } else {
        addNotification({
          type: 'error',
          title: 'Failed to restart container',
          message: result.message || 'Container restart failed',
        });
        return false;
      }
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Error restarting container',
        message: error instanceof Error ? error.message : 'Unknown error occurred',
      });
      return false;
    }
  };

  const removeContainer = async (deviceHostname: string, containerName: string, force = false): Promise<boolean> => {
    try {
      const result = await containerService.remove(deviceHostname, containerName, force);
      
      if (result.success) {
        await fetchContainers(deviceHostname);
        addNotification({
          type: 'success',
          title: 'Container removed',
          message: `Container ${containerName} has been removed`,
        });
        return true;
      } else {
        addNotification({
          type: 'error',
          title: 'Failed to remove container',
          message: result.message || 'Container removal failed',
        });
        return false;
      }
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Error removing container',
        message: error instanceof Error ? error.message : 'Unknown error occurred',
      });
      return false;
    }
  };

  // Auto-fetch containers on mount or when device changes
  useEffect(() => {
    fetchContainers(deviceHostname);
  }, [deviceHostname]);

  return {
    containers,
    loading,
    error,
    fetchContainers,
    startContainer,
    stopContainer,
    restartContainer,
    removeContainer,
    refetch: () => fetchContainers(deviceHostname),
  };
}

export function useContainer(deviceHostname: string | undefined, containerName: string | undefined) {
  const [container, setContainer] = useState<ContainerResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { addNotification } = useUIStore();

  const fetchContainer = async (hostname: string, name: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.get<ContainerResponse>(`/containers/${hostname}/${name}`);
      
      if (response.success && response.data) {
        setContainer(response.data);
      } else {
        setError(response.message || 'Failed to fetch container');
        addNotification({
          type: 'error',
          title: 'Error fetching container',
          message: response.message,
        });
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      setError(errorMessage);
      addNotification({
        type: 'error',
        title: 'Network error',
        message: 'Failed to connect to the server',
      });
    } finally {
      setLoading(false);
    }
  };

  const fetchContainerLogs = async (
    hostname: string, 
    name: string, 
    options?: { tail?: number; since?: string }
  ) => {
    try {
      const params = new URLSearchParams();
      if (options?.tail) params.set('tail', options.tail.toString());
      if (options?.since) params.set('since', options.since);
      
      const queryString = params.toString();
      const endpoint = `/containers/${hostname}/${name}/logs${queryString ? `?${queryString}` : ''}`;
      
      const response = await api.get<{ logs: string }>(endpoint);
      
      if (response.success && response.data) {
        return response.data.logs;
      } else {
        addNotification({
          type: 'error',
          title: 'Failed to fetch logs',
          message: response.message,
        });
        return '';
      }
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Error fetching logs',
        message: error instanceof Error ? error.message : 'Unknown error occurred',
      });
      return '';
    }
  };

  const fetchContainerStats = async (hostname: string, name: string) => {
    try {
      const response = await api.get(`/containers/${hostname}/${name}/stats`);
      
      if (response.success && response.data) {
        return response.data;
      } else {
        addNotification({
          type: 'error',
          title: 'Failed to fetch stats',
          message: response.message,
        });
        return null;
      }
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Error fetching stats',
        message: error instanceof Error ? error.message : 'Unknown error occurred',
      });
      return null;
    }
  };

  useEffect(() => {
    if (deviceHostname && containerName) {
      fetchContainer(deviceHostname, containerName);
    } else {
      setContainer(null);
      setError(null);
    }
  }, [deviceHostname, containerName]);

  return {
    container,
    loading,
    error,
    fetchContainerLogs,
    fetchContainerStats,
    refetch: deviceHostname && containerName 
      ? () => fetchContainer(deviceHostname, containerName)
      : () => {},
  };
}
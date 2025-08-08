import { useEffect, useState } from 'react';
import { api } from '@/services/api';
import { useUIStore } from '@/store/uiStore';
import type { 
  ProxyConfigResponse,
  ProxyConfigCreate,
  ProxyConfigUpdate,
  APIResponse 
} from '@infrastructor/shared-types';

export function useProxyConfigs(deviceHostname?: string) {
  const [configs, setConfigs] = useState<ProxyConfigResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { addNotification } = useUIStore();

  const fetchConfigs = async (hostname?: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const endpoint = hostname ? `/proxies?device=${hostname}` : '/proxies';
      const response = await api.get<{ configs: ProxyConfigResponse[] }>(endpoint);
      
      if (response.success && response.data) {
        setConfigs(response.data.configs || []);
      } else {
        setError(response.message || 'Failed to fetch proxy configurations');
        addNotification({
          type: 'error',
          title: 'Error fetching proxy configs',
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

  const createConfig = async (configData: ProxyConfigCreate): Promise<boolean> => {
    try {
      const response = await api.post<ProxyConfigResponse>('/proxies', configData);
      
      if (response.success && response.data) {
        setConfigs(prev => [...prev, response.data!]);
        addNotification({
          type: 'success',
          title: 'Proxy config created',
          message: `Configuration for ${response.data.service_name} has been created`,
        });
        return true;
      } else {
        addNotification({
          type: 'error',
          title: 'Failed to create proxy config',
          message: response.message,
        });
        return false;
      }
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Error creating proxy config',
        message: error instanceof Error ? error.message : 'Unknown error occurred',
      });
      return false;
    }
  };

  const updateConfig = async (configId: number, updates: ProxyConfigUpdate): Promise<boolean> => {
    try {
      const response = await api.put<ProxyConfigResponse>(`/proxies/${configId}`, updates);
      
      if (response.success && response.data) {
        setConfigs(prev => prev.map(config => 
          config.id === configId ? response.data! : config
        ));
        addNotification({
          type: 'success',
          title: 'Proxy config updated',
          message: `Configuration has been updated`,
        });
        return true;
      } else {
        addNotification({
          type: 'error',
          title: 'Failed to update proxy config',
          message: response.message,
        });
        return false;
      }
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Error updating proxy config',
        message: error instanceof Error ? error.message : 'Unknown error occurred',
      });
      return false;
    }
  };

  const deleteConfig = async (configId: number): Promise<boolean> => {
    try {
      const response = await api.delete(`/proxies/${configId}`);
      
      if (response.success) {
        setConfigs(prev => prev.filter(config => config.id !== configId));
        addNotification({
          type: 'success',
          title: 'Proxy config deleted',
          message: 'Configuration has been removed',
        });
        return true;
      } else {
        addNotification({
          type: 'error',
          title: 'Failed to delete proxy config',
          message: response.message,
        });
        return false;
      }
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Error deleting proxy config',
        message: error instanceof Error ? error.message : 'Unknown error occurred',
      });
      return false;
    }
  };

  const scanConfigs = async (deviceHostname?: string): Promise<boolean> => {
    try {
      const endpoint = deviceHostname 
        ? `/proxies/scan?device=${deviceHostname}` 
        : '/proxies/scan';
      const response = await api.post(endpoint);
      
      if (response.success) {
        await fetchConfigs(deviceHostname);
        addNotification({
          type: 'success',
          title: 'Proxy configs scanned',
          message: 'Configuration files have been scanned and synced',
        });
        return true;
      } else {
        addNotification({
          type: 'error',
          title: 'Failed to scan configs',
          message: response.message,
        });
        return false;
      }
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Error scanning configs',
        message: error instanceof Error ? error.message : 'Unknown error occurred',
      });
      return false;
    }
  };

  useEffect(() => {
    fetchConfigs(deviceHostname);
  }, [deviceHostname]);

  return {
    configs,
    loading,
    error,
    fetchConfigs,
    createConfig,
    updateConfig,
    deleteConfig,
    scanConfigs,
    refetch: () => fetchConfigs(deviceHostname),
  };
}

export function useProxyConfig(configId: number | undefined) {
  const [config, setConfig] = useState<ProxyConfigResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { addNotification } = useUIStore();

  const fetchConfig = async (id: number) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.get<ProxyConfigResponse>(`/proxies/${id}`);
      
      if (response.success && response.data) {
        setConfig(response.data);
      } else {
        setError(response.message || 'Failed to fetch proxy configuration');
        addNotification({
          type: 'error',
          title: 'Error fetching proxy config',
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

  useEffect(() => {
    if (configId) {
      fetchConfig(configId);
    } else {
      setConfig(null);
      setError(null);
    }
  }, [configId]);

  return {
    config,
    loading,
    error,
    refetch: configId ? () => fetchConfig(configId) : () => {},
  };
}
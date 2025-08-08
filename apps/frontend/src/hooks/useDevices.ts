import { useEffect, useState } from 'react';
import { deviceService } from '@/services';
import { useDeviceStore } from '@/store/deviceStore';
import { useUIStore } from '@/store/uiStore';
import type { 
  DeviceList, 
  DeviceResponse, 
  DeviceCreate, 
  DeviceUpdate
} from '@infrastructor/shared-types';

export function useDevices() {
  const { 
    devices, 
    loading, 
    error, 
    setDevices, 
    setLoading, 
    setError,
    addDevice: addDeviceToStore,
    updateDevice: updateDeviceInStore,
    removeDevice: removeDeviceFromStore,
  } = useDeviceStore();
  
  const { addNotification } = useUIStore();

  const fetchDevices = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const deviceList = await deviceService.list();
      setDevices(deviceList.items || []);
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

  const createDevice = async (deviceData: DeviceCreate): Promise<boolean> => {
    try {
      const device = await deviceService.create(deviceData);
      
      if (device) {
        addDeviceToStore(device);
        addNotification({
          type: 'success',
          title: 'Device created',
          message: `Device ${device.hostname} has been added`,
        });
        return true;
      } else {
        addNotification({
          type: 'error',
          title: 'Failed to create device',
          message: 'Device creation failed',
        });
        return false;
      }
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Error creating device',
        message: error instanceof Error ? error.message : 'Unknown error occurred',
      });
      return false;
    }
  };

  const updateDevice = async (hostname: string, updates: DeviceUpdate): Promise<boolean> => {
    try {
      const device = await deviceService.update(hostname, updates);
      
      if (device) {
        updateDeviceInStore(hostname, device);
        addNotification({
          type: 'success',
          title: 'Device updated',
          message: `Device ${hostname} has been updated`,
        });
        return true;
      } else {
        addNotification({
          type: 'error',
          title: 'Failed to update device',
          message: 'Device update failed',
        });
        return false;
      }
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Error updating device',
        message: error instanceof Error ? error.message : 'Unknown error occurred',
      });
      return false;
    }
  };

  const deleteDevice = async (hostname: string): Promise<boolean> => {
    try {
      const success = await deviceService.delete(hostname);
      
      if (success) {
        removeDeviceFromStore(hostname);
        addNotification({
          type: 'success',
          title: 'Device deleted',
          message: `Device ${hostname} has been removed`,
        });
        return true;
      } else {
        addNotification({
          type: 'error',
          title: 'Failed to delete device',
          message: 'Device deletion failed',
        });
        return false;
      }
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Error deleting device',
        message: error instanceof Error ? error.message : 'Unknown error occurred',
      });
      return false;
    }
  };

  // Auto-fetch devices on mount
  useEffect(() => {
    fetchDevices();
  }, []);

  return {
    devices,
    loading,
    error,
    fetchDevices,
    createDevice,
    updateDevice,
    deleteDevice,
    refetch: fetchDevices,
  };
}

export function useDevice(hostname: string | undefined) {
  const [device, setDevice] = useState<DeviceResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { addNotification } = useUIStore();

  const fetchDevice = async (deviceHostname: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const deviceData = await deviceService.get(deviceHostname);
      
      if (deviceData) {
        setDevice(deviceData);
      } else {
        setError('Failed to fetch device');
        addNotification({
          type: 'error',
          title: 'Error fetching device',
          message: 'Device not found or failed to fetch',
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
    if (hostname) {
      fetchDevice(hostname);
    } else {
      setDevice(null);
      setError(null);
    }
  }, [hostname]);

  return {
    device,
    loading,
    error,
    refetch: hostname ? () => fetchDevice(hostname) : () => {},
  };
}
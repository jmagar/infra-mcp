import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { DeviceResponse } from '@infrastructor/shared-types';

interface DeviceStore {
  // State
  devices: DeviceResponse[];
  selectedDevice: DeviceResponse | null;
  loading: boolean;
  error: string | null;
  filters: {
    search: string;
    status: string;
    type: string;
  };

  // Actions
  setDevices: (devices: DeviceResponse[]) => void;
  addDevice: (device: DeviceResponse) => void;
  updateDevice: (hostname: string, updates: Partial<DeviceResponse>) => void;
  removeDevice: (hostname: string) => void;
  selectDevice: (device: DeviceResponse | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setFilters: (filters: Partial<DeviceStore['filters']>) => void;
  clearFilters: () => void;
  
  // Computed
  filteredDevices: () => DeviceResponse[];
}

export const useDeviceStore = create<DeviceStore>()(
  devtools(
    (set, get) => ({
      // Initial state
      devices: [],
      selectedDevice: null,
      loading: false,
      error: null,
      filters: {
        search: '',
        status: '',
        type: '',
      },

      // Actions
      setDevices: (devices) => set({ devices }),
      
      addDevice: (device) =>
        set((state) => ({
          devices: [...state.devices, device],
        })),
      
      updateDevice: (hostname, updates) =>
        set((state) => ({
          devices: state.devices.map((device) =>
            device.hostname === hostname
              ? { ...device, ...updates }
              : device
          ),
          selectedDevice:
            state.selectedDevice?.hostname === hostname
              ? { ...state.selectedDevice, ...updates }
              : state.selectedDevice,
        })),
      
      removeDevice: (hostname) =>
        set((state) => ({
          devices: state.devices.filter((device) => device.hostname !== hostname),
          selectedDevice:
            state.selectedDevice?.hostname === hostname
              ? null
              : state.selectedDevice,
        })),
      
      selectDevice: (device) => set({ selectedDevice: device }),
      
      setLoading: (loading) => set({ loading }),
      
      setError: (error) => set({ error }),
      
      setFilters: (newFilters) =>
        set((state) => ({
          filters: { ...state.filters, ...newFilters },
        })),
      
      clearFilters: () =>
        set({
          filters: {
            search: '',
            status: '',
            type: '',
          },
        }),
      
      // Computed
      filteredDevices: () => {
        const { devices, filters } = get();
        return devices.filter((device) => {
          const matchesSearch =
            !filters.search ||
            device.hostname.toLowerCase().includes(filters.search.toLowerCase()) ||
            device.ip_address?.toLowerCase().includes(filters.search.toLowerCase());
          
          const matchesStatus =
            !filters.status || device.status === filters.status;
          
          const matchesType =
            !filters.type || device.device_type === filters.type;
          
          return matchesSearch && matchesStatus && matchesType;
        });
      },
    }),
    {
      name: 'device-store',
    }
  )
);
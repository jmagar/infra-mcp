import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { ContainerResponse, ContainerStats } from '@infrastructor/shared-types';

interface ContainerStore {
  // State
  containers: ContainerResponse[];
  totalCount: number;
  selectedContainer: ContainerResponse | null;
  containerStats: Record<string, ContainerStats>;
  loading: boolean;
  error: string | null;
  filters: {
    search: string;
    status: string;
    device: string;
  };

  // Actions
  setContainers: (containers: ContainerResponse[]) => void;
  setTotalCount: (count: number) => void;
  addContainer: (container: ContainerResponse) => void;
  updateContainer: (id: string, updates: Partial<ContainerResponse>) => void;
  removeContainer: (id: string) => void;
  selectContainer: (container: ContainerResponse | null) => void;
  setContainerStats: (containerId: string, stats: ContainerStats) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setFilters: (filters: Partial<ContainerStore['filters']>) => void;
  clearFilters: () => void;
  
  // Computed
  filteredContainers: () => ContainerResponse[];
  containersByDevice: () => Record<string, ContainerResponse[]>;
}

export const useContainerStore = create<ContainerStore>()(
  devtools(
    (set, get) => ({
      // Initial state
      containers: [],
      totalCount: 0,
      selectedContainer: null,
      containerStats: {},
      loading: false,
      error: null,
      filters: {
        search: '',
        status: '',
        device: '',
      },

      // Actions
      setContainers: (containers) => set({ containers }),
      setTotalCount: (totalCount) => set({ totalCount }),
      
      addContainer: (container) =>
        set((state) => ({
          containers: [...state.containers, container],
        })),
      
      updateContainer: (id, updates) =>
        set((state) => ({
          containers: state.containers.map((container) =>
            container.id === id
              ? { ...container, ...updates }
              : container
          ),
          selectedContainer:
            state.selectedContainer?.id === id
              ? { ...state.selectedContainer, ...updates }
              : state.selectedContainer,
        })),
      
      removeContainer: (id) =>
        set((state) => ({
          containers: state.containers.filter((container) => container.id !== id),
          selectedContainer:
            state.selectedContainer?.id === id
              ? null
              : state.selectedContainer,
        })),
      
      selectContainer: (container) => set({ selectedContainer: container }),
      
      setContainerStats: (containerId, stats) =>
        set((state) => ({
          containerStats: {
            ...state.containerStats,
            [containerId]: stats,
          },
        })),
      
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
            device: '',
          },
        }),
      
      // Computed
      filteredContainers: () => {
        const { containers, filters } = get();
        return containers.filter((container) => {
          const matchesSearch =
            !filters.search ||
            container.name.toLowerCase().includes(filters.search.toLowerCase()) ||
            container.image?.toLowerCase().includes(filters.search.toLowerCase());
          
          const matchesStatus =
            !filters.status || container.status === filters.status;
          
          const matchesDevice =
            !filters.device || container.device_hostname === filters.device;
          
          return matchesSearch && matchesStatus && matchesDevice;
        });
      },
      
      containersByDevice: () => {
        const { containers } = get();
        return containers.reduce((acc, container) => {
          const device = container.device_hostname;
          if (!acc[device]) {
            acc[device] = [];
          }
          acc[device].push(container);
          return acc;
        }, {} as Record<string, ContainerResponse[]>);
      },
    }),
    {
      name: 'container-store',
    }
  )
);
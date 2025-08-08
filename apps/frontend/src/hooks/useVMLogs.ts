/**
 * VM Logs Hook
 * React hook for VM logs operations
 */

import { useState, useEffect, useCallback } from 'react';
import { vmService } from '@/services';

interface VMLogsData {
  hostname: string;
  log_source: string;
  logs: string;
  success: boolean;
}

interface VMSpecificLogsData extends VMLogsData {
  vm_name: string;
}

interface UseVMLogsResult {
  // Data
  logs: VMLogsData | null;
  vmLogs: Record<string, VMSpecificLogsData> | null;
  availableVMs: string[] | null;
  
  // State
  loading: boolean;
  error: string | null;
  
  // Actions
  refetch: () => Promise<void>;
  getVMSpecificLogs: (vmName: string) => Promise<void>;
  refreshVMsList: () => Promise<void>;
}

export function useVMLogs(hostname?: string): UseVMLogsResult {
  // Data state
  const [logs, setLogs] = useState<VMLogsData | null>(null);
  const [vmLogs, setVmLogs] = useState<Record<string, VMSpecificLogsData> | null>(null);
  const [availableVMs, setAvailableVMs] = useState<string[] | null>(null);
  
  // UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch libvirt logs
  const fetchLibvirtLogs = useCallback(async () => {
    if (!hostname) return;
    
    try {
      setError(null);
      const result = await vmService.getLogs(hostname);
      setLogs(result);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch VM logs';
      setError(message);
      console.error('Error fetching VM logs:', error);
    }
  }, [hostname]);

  // Fetch specific VM logs
  const getVMSpecificLogs = useCallback(async (vmName: string) => {
    if (!hostname) return;
    
    try {
      setError(null);
      const result = await vmService.getVMSpecificLogs(hostname, vmName);
      
      setVmLogs(prev => ({
        ...prev,
        [vmName]: result as VMSpecificLogsData,
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : `Failed to fetch logs for VM ${vmName}`;
      setError(message);
      console.error(`Error fetching VM logs for ${vmName}:`, error);
    }
  }, [hostname]);

  // Discover available VMs (this would need to be implemented in the backend)
  const refreshVMsList = useCallback(async () => {
    if (!hostname) return;
    
    try {
      setError(null);
      // This would call a backend endpoint to discover VMs
      // For now, we'll extract VM names from log content or use a mock list
      // In a real implementation, this might call `virsh list --all` via SSH
      
      // Mock data for now - in reality this would come from the backend
      const mockVMs = ['vm1', 'vm2', 'web-server', 'database-vm'];
      setAvailableVMs(mockVMs);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to discover VMs';
      setError(message);
      console.error('Error discovering VMs:', error);
    }
  }, [hostname]);

  // Refetch all data
  const refetch = useCallback(async () => {
    if (!hostname) return;
    
    setLoading(true);
    try {
      await Promise.all([
        fetchLibvirtLogs(),
        refreshVMsList(),
      ]);
    } finally {
      setLoading(false);
    }
  }, [hostname, fetchLibvirtLogs, refreshVMsList]);

  // Initial load
  useEffect(() => {
    if (hostname) {
      refetch();
    }
  }, [hostname, refetch]);

  return {
    // Data
    logs,
    vmLogs,
    availableVMs,
    
    // State
    loading,
    error,
    
    // Actions
    refetch,
    getVMSpecificLogs,
    refreshVMsList,
  };
}
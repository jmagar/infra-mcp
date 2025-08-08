/**
 * ZFS Hook
 * React hook for ZFS management operations
 */

import { useState, useEffect, useCallback } from 'react';
import { zfsService } from '@/services';
import type {
  ZFSPoolResponse,
  ZFSDatasetResponse,
  ZFSSnapshotResponse,
  ZFSHealthCheck,
  ZFSARCStats,
  ZFSReport,
  ZFSSnapshotUsageAnalysis,
  ZFSOptimizationSuggestions,
} from '@infrastructor/shared-types';

interface UseZFSResult {
  // Data
  pools: ZFSPoolResponse[] | null;
  datasets: ZFSDatasetResponse[] | null;
  snapshots: ZFSSnapshotResponse[] | null;
  healthCheck: ZFSHealthCheck | null;
  arcStats: ZFSARCStats | null;
  report: ZFSReport | null;
  snapshotUsage: ZFSSnapshotUsageAnalysis | null;
  optimizationSuggestions: ZFSOptimizationSuggestions | null;
  
  // State
  loading: boolean;
  error: string | null;
  
  // Actions
  refetch: () => Promise<void>;
  refreshPools: () => Promise<void>;
  refreshDatasets: () => Promise<void>;
  refreshSnapshots: () => Promise<void>;
  refreshHealth: () => Promise<void>;
  refreshArcStats: () => Promise<void>;
  
  // Pool operations
  getPoolStatus: (poolName: string) => Promise<any>;
  
  // Dataset operations
  getDatasetProperties: (datasetName: string) => Promise<any>;
  
  // Snapshot operations
  createSnapshot: (datasetName: string, snapshotName: string, recursive?: boolean) => Promise<boolean>;
  deleteSnapshot: (snapshotName: string) => Promise<boolean>;
  cloneSnapshot: (snapshotName: string, cloneName: string) => Promise<boolean>;
  sendSnapshot: (snapshotName: string, destination?: string, incremental?: boolean) => Promise<boolean>;
  
  // Reports and analysis
  generateReport: () => Promise<void>;
  analyzeSnapshotUsage: () => Promise<void>;
  getOptimizationSuggestions: () => Promise<void>;
}

export function useZFS(hostname?: string): UseZFSResult {
  // Data state
  const [pools, setPools] = useState<ZFSPoolResponse[] | null>(null);
  const [datasets, setDatasets] = useState<ZFSDatasetResponse[] | null>(null);
  const [snapshots, setSnapshots] = useState<ZFSSnapshotResponse[] | null>(null);
  const [healthCheck, setHealthCheck] = useState<ZFSHealthCheck | null>(null);
  const [arcStats, setArcStats] = useState<ZFSARCStats | null>(null);
  const [report, setReport] = useState<ZFSReport | null>(null);
  const [snapshotUsage, setSnapshotUsage] = useState<ZFSSnapshotUsageAnalysis | null>(null);
  const [optimizationSuggestions, setOptimizationSuggestions] = useState<ZFSOptimizationSuggestions | null>(null);
  
  // UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch pools
  const refreshPools = useCallback(async () => {
    if (!hostname) return;
    
    try {
      setError(null);
      const result = await zfsService.listPools(hostname);
      setPools(result.pools || []);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch pools';
      setError(message);
      console.error('Error fetching ZFS pools:', error);
    }
  }, [hostname]);

  // Fetch datasets
  const refreshDatasets = useCallback(async () => {
    if (!hostname) return;
    
    try {
      setError(null);
      const result = await zfsService.listDatasets(hostname);
      setDatasets(result.datasets || []);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch datasets';
      setError(message);
      console.error('Error fetching ZFS datasets:', error);
    }
  }, [hostname]);

  // Fetch snapshots
  const refreshSnapshots = useCallback(async () => {
    if (!hostname) return;
    
    try {
      setError(null);
      const result = await zfsService.listSnapshots(hostname);
      setSnapshots(result.snapshots || []);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch snapshots';
      setError(message);
      console.error('Error fetching ZFS snapshots:', error);
    }
  }, [hostname]);

  // Fetch health check
  const refreshHealth = useCallback(async () => {
    if (!hostname) return;
    
    try {
      setError(null);
      const health = await zfsService.checkHealth(hostname);
      setHealthCheck(health);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch health check';
      setError(message);
      console.error('Error fetching ZFS health:', error);
    }
  }, [hostname]);

  // Fetch ARC stats
  const refreshArcStats = useCallback(async () => {
    if (!hostname) return;
    
    try {
      setError(null);
      const stats = await zfsService.getArcStats(hostname);
      setArcStats(stats);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch ARC stats';
      setError(message);
      console.error('Error fetching ARC stats:', error);
    }
  }, [hostname]);

  // Get pool status
  const getPoolStatus = useCallback(async (poolName: string) => {
    if (!hostname) throw new Error('No hostname provided');
    
    try {
      setError(null);
      return await zfsService.getPoolStatus(hostname, poolName);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to get pool status';
      setError(message);
      throw error;
    }
  }, [hostname]);

  // Get dataset properties
  const getDatasetProperties = useCallback(async (datasetName: string) => {
    if (!hostname) throw new Error('No hostname provided');
    
    try {
      setError(null);
      return await zfsService.getDatasetProperties(hostname, datasetName);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to get dataset properties';
      setError(message);
      throw error;
    }
  }, [hostname]);

  // Create snapshot
  const createSnapshot = useCallback(async (datasetName: string, snapshotName: string, recursive = false): Promise<boolean> => {
    if (!hostname) return false;
    
    try {
      setLoading(true);
      setError(null);
      
      await zfsService.createSnapshot(hostname, datasetName, snapshotName, recursive);
      await refreshSnapshots(); // Refresh the list
      return true;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to create snapshot';
      setError(message);
      console.error('Error creating snapshot:', error);
      return false;
    } finally {
      setLoading(false);
    }
  }, [hostname, refreshSnapshots]);

  // Delete snapshot
  const deleteSnapshot = useCallback(async (snapshotName: string): Promise<boolean> => {
    if (!hostname) return false;
    
    try {
      setLoading(true);
      setError(null);
      
      await zfsService.deleteSnapshot(hostname, snapshotName);
      await refreshSnapshots(); // Refresh the list
      return true;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to delete snapshot';
      setError(message);
      console.error('Error deleting snapshot:', error);
      return false;
    } finally {
      setLoading(false);
    }
  }, [hostname, refreshSnapshots]);

  // Clone snapshot
  const cloneSnapshot = useCallback(async (snapshotName: string, cloneName: string): Promise<boolean> => {
    if (!hostname) return false;
    
    try {
      setLoading(true);
      setError(null);
      
      await zfsService.cloneSnapshot(hostname, snapshotName, cloneName);
      await refreshDatasets(); // Refresh datasets as clone creates a new dataset
      return true;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to clone snapshot';
      setError(message);
      console.error('Error cloning snapshot:', error);
      return false;
    } finally {
      setLoading(false);
    }
  }, [hostname, refreshDatasets]);

  // Send snapshot
  const sendSnapshot = useCallback(async (snapshotName: string, destination?: string, incremental = false): Promise<boolean> => {
    if (!hostname) return false;
    
    try {
      setLoading(true);
      setError(null);
      
      await zfsService.sendSnapshot(hostname, snapshotName, destination, incremental);
      return true;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to send snapshot';
      setError(message);
      console.error('Error sending snapshot:', error);
      return false;
    } finally {
      setLoading(false);
    }
  }, [hostname]);

  // Generate report
  const generateReport = useCallback(async () => {
    if (!hostname) return;
    
    try {
      setLoading(true);
      setError(null);
      
      const reportData = await zfsService.generateReport(hostname);
      setReport(reportData);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to generate report';
      setError(message);
      console.error('Error generating ZFS report:', error);
    } finally {
      setLoading(false);
    }
  }, [hostname]);

  // Analyze snapshot usage
  const analyzeSnapshotUsage = useCallback(async () => {
    if (!hostname) return;
    
    try {
      setLoading(true);
      setError(null);
      
      const analysis = await zfsService.analyzeSnapshotUsage(hostname);
      setSnapshotUsage(analysis);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to analyze snapshot usage';
      setError(message);
      console.error('Error analyzing snapshot usage:', error);
    } finally {
      setLoading(false);
    }
  }, [hostname]);

  // Get optimization suggestions
  const getOptimizationSuggestions = useCallback(async () => {
    if (!hostname) return;
    
    try {
      setLoading(true);
      setError(null);
      
      const suggestions = await zfsService.getOptimizationSuggestions(hostname);
      setOptimizationSuggestions(suggestions);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to get optimization suggestions';
      setError(message);
      console.error('Error getting optimization suggestions:', error);
    } finally {
      setLoading(false);
    }
  }, [hostname]);

  // Refetch all data
  const refetch = useCallback(async () => {
    if (!hostname) return;
    
    setLoading(true);
    try {
      await Promise.all([
        refreshPools(),
        refreshDatasets(),
        refreshSnapshots(),
        refreshHealth(),
        refreshArcStats(),
      ]);
    } finally {
      setLoading(false);
    }
  }, [hostname, refreshPools, refreshDatasets, refreshSnapshots, refreshHealth, refreshArcStats]);

  // Initial load
  useEffect(() => {
    if (hostname) {
      refetch();
    }
  }, [hostname, refetch]);

  return {
    // Data
    pools,
    datasets,
    snapshots,
    healthCheck,
    arcStats,
    report,
    snapshotUsage,
    optimizationSuggestions,
    
    // State
    loading,
    error,
    
    // Actions
    refetch,
    refreshPools,
    refreshDatasets,
    refreshSnapshots,
    refreshHealth,
    refreshArcStats,
    
    // Pool operations
    getPoolStatus,
    
    // Dataset operations
    getDatasetProperties,
    
    // Snapshot operations
    createSnapshot,
    deleteSnapshot,
    cloneSnapshot,
    sendSnapshot,
    
    // Reports and analysis
    generateReport,
    analyzeSnapshotUsage,
    getOptimizationSuggestions,
  };
}
/**
 * ZFS Service
 * API methods for ZFS management
 */

import { zfsApi } from './api';

export const zfsService = {
  // List ZFS pools
  async listPools(hostname: string): Promise<any[] | null> {
    try {
      const response = await zfsApi.listPools(hostname);
      if (response.success && response.data) {
        return response.data as any[];
      }
      return null;
    } catch (error) {
      console.error(`Failed to get ZFS pools for ${hostname}:`, error);
      return null;
    }
  },

  // Get pool status
  async getPoolStatus(hostname: string, poolName: string): Promise<any | null> {
    try {
      const response = await zfsApi.getPoolStatus(hostname, poolName);
      if (response.success && response.data) {
        return response.data;
      }
      return null;
    } catch (error) {
      console.error(`Failed to get ZFS pool status for ${hostname}/${poolName}:`, error);
      return null;
    }
  },

  // List datasets
  async listDatasets(hostname: string): Promise<any[] | null> {
    try {
      const response = await zfsApi.listDatasets(hostname);
      if (response.success && response.data) {
        return response.data as any[];
      }
      return null;
    } catch (error) {
      console.error(`Failed to get ZFS datasets for ${hostname}:`, error);
      return null;
    }
  },

  // Get dataset properties
  async getDatasetProperties(hostname: string, datasetName: string): Promise<any | null> {
    try {
      const response = await zfsApi.getDatasetProperties(hostname, datasetName);
      if (response.success && response.data) {
        return response.data;
      }
      return null;
    } catch (error) {
      console.error(`Failed to get ZFS dataset properties for ${hostname}/${datasetName}:`, error);
      return null;
    }
  },

  // List snapshots
  async listSnapshots(hostname: string): Promise<any[] | null> {
    try {
      const response = await zfsApi.listSnapshots(hostname);
      if (response.success && response.data) {
        return response.data as any[];
      }
      return null;
    } catch (error) {
      console.error(`Failed to get ZFS snapshots for ${hostname}:`, error);
      return null;
    }
  },

  // Create snapshot
  async createSnapshot(hostname: string, data: { dataset_name: string; snapshot_name: string; recursive?: boolean }): Promise<boolean> {
    try {
      const response = await zfsApi.createSnapshot(hostname, data);
      return response.success;
    } catch (error) {
      console.error(`Failed to create ZFS snapshot for ${hostname}:`, error);
      throw error;
    }
  },

  // Clone snapshot
  async cloneSnapshot(hostname: string, snapshotName: string, data: { clone_name: string }): Promise<boolean> {
    try {
      const response = await zfsApi.cloneSnapshot(hostname, snapshotName, data);
      return response.success;
    } catch (error) {
      console.error(`Failed to clone ZFS snapshot ${snapshotName} for ${hostname}:`, error);
      throw error;
    }
  },

  // Send snapshot
  async sendSnapshot(hostname: string, snapshotName: string, data: { destination?: string; incremental?: boolean }): Promise<any> {
    try {
      const response = await zfsApi.sendSnapshot(hostname, snapshotName, data);
      if (response.success && response.data) {
        return response.data;
      }
      return null;
    } catch (error) {
      console.error(`Failed to send ZFS snapshot ${snapshotName} for ${hostname}:`, error);
      throw error;
    }
  },

  // Receive snapshot
  async receiveSnapshot(hostname: string, data: { dataset_name: string }): Promise<boolean> {
    try {
      const response = await zfsApi.receiveSnapshot(hostname, data);
      return response.success;
    } catch (error) {
      console.error(`Failed to receive ZFS snapshot for ${hostname}:`, error);
      throw error;
    }
  },

  // Diff snapshots
  async diffSnapshots(hostname: string, snapshotName: string, data: { snapshot2: string }): Promise<any> {
    try {
      const response = await zfsApi.diffSnapshots(hostname, snapshotName, data);
      if (response.success && response.data) {
        return response.data;
      }
      return null;
    } catch (error) {
      console.error(`Failed to diff ZFS snapshots for ${hostname}:`, error);
      return null;
    }
  },

  // Get ZFS health
  async getHealth(hostname: string): Promise<any | null> {
    try {
      const response = await zfsApi.getHealth(hostname);
      if (response.success && response.data) {
        return response.data;
      }
      return null;
    } catch (error) {
      console.error(`Failed to get ZFS health for ${hostname}:`, error);
      return null;
    }
  },

  // Get ARC stats
  async getARCStats(hostname: string): Promise<any | null> {
    try {
      const response = await zfsApi.getARCStats(hostname);
      if (response.success && response.data) {
        return response.data;
      }
      return null;
    } catch (error) {
      console.error(`Failed to get ZFS ARC stats for ${hostname}:`, error);
      return null;
    }
  },

  // Get ZFS events
  async getEvents(hostname: string): Promise<any | null> {
    try {
      const response = await zfsApi.getEvents(hostname);
      if (response.success && response.data) {
        return response.data;
      }
      return null;
    } catch (error) {
      console.error(`Failed to get ZFS events for ${hostname}:`, error);
      return null;
    }
  },

  // Get ZFS report
  async getReport(hostname: string): Promise<any | null> {
    try {
      const response = await zfsApi.getReport(hostname);
      if (response.success && response.data) {
        return response.data;
      }
      return null;
    } catch (error) {
      console.error(`Failed to get ZFS report for ${hostname}:`, error);
      return null;
    }
  },

  // Get snapshot usage
  async getSnapshotUsage(hostname: string): Promise<any | null> {
    try {
      const response = await zfsApi.getSnapshotUsage(hostname);
      if (response.success && response.data) {
        return response.data;
      }
      return null;
    } catch (error) {
      console.error(`Failed to get ZFS snapshot usage for ${hostname}:`, error);
      return null;
    }
  },

  // Optimize ZFS settings
  async optimize(hostname: string): Promise<any | null> {
    try {
      const response = await zfsApi.optimize(hostname);
      if (response.success && response.data) {
        return response.data;
      }
      return null;
    } catch (error) {
      console.error(`Failed to optimize ZFS settings for ${hostname}:`, error);
      throw error;
    }
  },
};
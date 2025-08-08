/**
 * ZFS Service
 * API methods for ZFS filesystem management
 */

import { api } from './api';
import type {
  ZFSPoolResponse,
  ZFSDatasetResponse,
  ZFSSnapshotResponse,
  ZFSHealthCheck,
  PaginationParams,
} from '@infrastructor/shared-types';

export const zfsService = {
  // Pool Management
  pools: {
    // List all ZFS pools on a device
    async list(deviceId: string): Promise<ZFSPoolResponse[]> {
      const response = await api.get<ZFSPoolResponse[]>(`/zfs/${deviceId}/pools`);
      return response.data || [];
    },

    // Get detailed status for a specific pool
    async getStatus(deviceId: string, poolName: string): Promise<ZFSPoolResponse | null> {
      const response = await api.get<ZFSPoolResponse>(`/zfs/${deviceId}/pools/${poolName}/status`);
      return response.data || null;
    },
  },

  // Dataset Management
  datasets: {
    // List ZFS datasets, optionally filtered by pool
    async list(deviceId: string, poolName?: string): Promise<ZFSDatasetResponse[]> {
      const url = poolName 
        ? `/zfs/${deviceId}/datasets?pool_name=${poolName}`
        : `/zfs/${deviceId}/datasets`;
      const response = await api.get<ZFSDatasetResponse[]>(url);
      return response.data || [];
    },

    // Get properties for a specific dataset
    async getProperties(deviceId: string, datasetName: string): Promise<Record<string, any> | null> {
      const response = await api.get<Record<string, any>>(
        `/zfs/${deviceId}/datasets/${datasetName}/properties`
      );
      return response.data || null;
    },
  },

  // Snapshot Management
  snapshots: {
    // List ZFS snapshots, optionally filtered by dataset
    async list(deviceId: string, datasetName?: string): Promise<ZFSSnapshotResponse[]> {
      const url = datasetName 
        ? `/zfs/${deviceId}/snapshots?dataset_name=${datasetName}`
        : `/zfs/${deviceId}/snapshots`;
      const response = await api.get<ZFSSnapshotResponse[]>(url);
      return response.data || [];
    },

    // Create a new snapshot
    async create(
      deviceId: string,
      datasetName: string,
      snapshotName: string,
      recursive?: boolean
    ): Promise<{ success: boolean; message?: string }> {
      const response = await api.post<{ success: boolean; message?: string }>(
        `/zfs/${deviceId}/snapshots`,
        { dataset_name: datasetName, snapshot_name: snapshotName, recursive }
      );
      return response.data || { success: false, message: 'Snapshot creation failed' };
    },

    // Clone a snapshot
    async clone(
      deviceId: string,
      snapshotName: string,
      cloneName: string
    ): Promise<{ success: boolean; message?: string }> {
      const response = await api.post<{ success: boolean; message?: string }>(
        `/zfs/${deviceId}/snapshots/${snapshotName}/clone`,
        { clone_name: cloneName }
      );
      return response.data || { success: false, message: 'Snapshot clone failed' };
    },

    // Send snapshot for replication
    async send(
      deviceId: string,
      snapshotName: string,
      params?: { destination?: string; incremental?: boolean }
    ): Promise<{ success: boolean; message?: string; size?: number }> {
      const response = await api.post<{ 
        success: boolean; 
        message?: string; 
        size?: number;
      }>(`/zfs/${deviceId}/snapshots/${snapshotName}/send`, params);
      return response.data || { success: false, message: 'Snapshot send failed' };
    },

    // Receive snapshot stream
    async receive(
      deviceId: string,
      datasetName: string
    ): Promise<{ success: boolean; message?: string }> {
      const response = await api.post<{ success: boolean; message?: string }>(
        `/zfs/${deviceId}/snapshots/receive`,
        { dataset_name: datasetName }
      );
      return response.data || { success: false, message: 'Snapshot receive failed' };
    },

    // Compare differences between snapshots
    async diff(
      deviceId: string,
      snapshot1: string,
      snapshot2: string
    ): Promise<{ changes: Array<{ type: string; path: string }>; summary: any } | null> {
      const response = await api.get<{ 
        changes: Array<{ type: string; path: string }>; 
        summary: any;
      }>(`/zfs/${deviceId}/snapshots/diff`, {
        params: { snapshot1, snapshot2 }
      });
      return response.data || null;
    },
  },

  // Health and Monitoring
  health: {
    // Comprehensive ZFS health check
    async check(deviceId: string): Promise<ZFSHealthCheck | null> {
      const response = await api.get<ZFSHealthCheck>(`/zfs/${deviceId}/health`);
      return response.data || null;
    },

    // Get ZFS ARC statistics
    async getArcStats(deviceId: string): Promise<Record<string, any> | null> {
      const response = await api.get<Record<string, any>>(`/zfs/${deviceId}/arc-stats`);
      return response.data || null;
    },

    // Monitor ZFS events
    async getEvents(deviceId: string): Promise<Array<{ 
      time: string; 
      class: string; 
      subclass: string; 
      details: Record<string, any>;
    }>> {
      const response = await api.get<Array<{
        time: string;
        class: string;
        subclass: string;
        details: Record<string, any>;
      }>>(`/zfs/${deviceId}/events`);
      return response.data || [];
    },
  },

  // Analysis and Optimization
  analysis: {
    // Generate comprehensive ZFS report
    async generateReport(deviceId: string): Promise<{
      pools: any[];
      datasets: any[];
      snapshots: any[];
      health: any;
      recommendations: string[];
    } | null> {
      const response = await api.get<{
        pools: any[];
        datasets: any[];
        snapshots: any[];
        health: any;
        recommendations: string[];
      }>(`/zfs/${deviceId}/report`);
      return response.data || null;
    },

    // Analyze snapshot space usage
    async analyzeSnapshots(deviceId: string): Promise<{
      total_size: number;
      snapshots_by_dataset: Record<string, any>;
      cleanup_recommendations: Array<{ dataset: string; snapshots: string[]; space_saved: number }>;
    } | null> {
      const response = await api.get<{
        total_size: number;
        snapshots_by_dataset: Record<string, any>;
        cleanup_recommendations: Array<{ dataset: string; snapshots: string[]; space_saved: number }>;
      }>(`/zfs/${deviceId}/analyze/snapshots`);
      return response.data || null;
    },

    // Get ZFS optimization recommendations
    async getOptimizations(deviceId: string): Promise<{
      recommendations: Array<{
        category: string;
        priority: string;
        description: string;
        command?: string;
      }>;
      current_settings: Record<string, any>;
    } | null> {
      const response = await api.get<{
        recommendations: Array<{
          category: string;
          priority: string;
          description: string;
          command?: string;
        }>;
        current_settings: Record<string, any>;
      }>(`/zfs/${deviceId}/optimize`);
      return response.data || null;
    },
  },
};
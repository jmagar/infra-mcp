/**
 * Custom hook for Docker Compose operations
 */

import { useState, useEffect } from 'react';
import { composeApi } from '@/services/api';
import type { ComposeStack, ComposeModifyRequest, ComposeDeployRequest } from '@infrastructor/shared-types';

export function useCompose() {
  const [composeStacks, setComposeStacks] = useState<ComposeStack[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStacks = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await composeApi.list();
      setComposeStacks(response.data.items || []);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch compose stacks';
      setError(errorMessage);
      console.error('Error fetching compose stacks:', err);
    } finally {
      setLoading(false);
    }
  };

  const deployStack = async (
    deviceHostname: string, 
    stackName: string, 
    content?: string, 
    path?: string
  ) => {
    const deployData: ComposeDeployRequest = {
      device: deviceHostname,
      compose_content: content || '',
      deployment_path: path,
      service_name: stackName,
      start_services: true,
      pull_images: true,
    };
    
    await composeApi.deploy(deployData);
  };

  const stopStack = async (deviceHostname: string, stackName: string) => {
    await composeApi.stop(deviceHostname, stackName);
  };

  const removeStack = async (deviceHostname: string, stackName: string) => {
    await composeApi.remove(deviceHostname, stackName);
  };

  const modifyStack = async (
    deviceHostname: string,
    stackName: string,
    content: string,
    targetDevice?: string
  ) => {
    const modifyData: ComposeModifyRequest = {
      compose_content: content,
      target_device: targetDevice || deviceHostname,
      service_name: stackName,
    };
    
    await composeApi.modify(modifyData);
  };

  const scanPorts = async (deviceHostname: string) => {
    return await composeApi.scanPorts(deviceHostname);
  };

  const scanNetworks = async (deviceHostname: string) => {
    return await composeApi.scanNetworks(deviceHostname);
  };

  useEffect(() => {
    fetchStacks();
  }, []);

  return {
    composeStacks,
    loading,
    error,
    refetch: fetchStacks,
    deployStack,
    stopStack,
    removeStack,
    modifyStack,
    scanPorts,
    scanNetworks,
  };
}
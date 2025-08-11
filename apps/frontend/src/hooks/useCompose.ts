/**
 * Custom hook for Docker Compose operations
 */

import { useState, useEffect } from 'react';
import { composeApi } from '@/services/api';

export function useCompose() {
  const [composeStacks, setComposeStacks] = useState<Array<Record<string, unknown>>>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // No-op placeholder until backend list endpoint is available
  const fetchStacks = async () => {
    setLoading(false);
    setError(null);
    setComposeStacks([]);
  };

  const deployStack = async (
    deviceHostname: string, 
    stackName: string, 
    content?: string, 
    path?: string
  ) => {
    const deployData = {
      device: deviceHostname,
      compose_content: content || '',
      deployment_path: path,
      service_name: stackName,
      start_services: true,
      pull_images: true,
    };
    await composeApi.deploy(deployData);
  };

  // Placeholders for future implementations
  const stopStack = async (_deviceHostname: string, _stackName: string) => {
    void _deviceHostname;
    void _stackName;
  };
  const removeStack = async (_deviceHostname: string, _stackName: string) => {
    void _deviceHostname;
    void _stackName;
  };

  const modifyStack = async (
    deviceHostname: string,
    stackName: string,
    content: string,
    targetDevice?: string
  ) => {
    const modifyData = {
      compose_content: content,
      target_device: targetDevice || deviceHostname,
      service_name: stackName,
    };
    await composeApi.modify(modifyData);
  };

  const scanPorts = async (deviceHostname: string) => {
    return await composeApi.scanPorts({ device: deviceHostname });
  };

  const scanNetworks = async (deviceHostname: string) => {
    return await composeApi.scanNetworks({ device: deviceHostname });
  };

  useEffect(() => {
    // no-op
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
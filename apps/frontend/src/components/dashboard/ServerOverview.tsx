import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Server, HardDrive, Package, CheckCircle, AlertCircle } from 'lucide-react';
import { useEffect, useState } from 'react';
import { deviceApi, containerApi } from '@/services/api';

interface Device {
  id: string;
  hostname: string;
  ip_address?: string;
  device_type: string;
  status: 'online' | 'offline' | 'unknown';
  monitoring_enabled: boolean;
  last_seen: string | null;
  containers?: {
    total: number;
    running: number;
  };
}

interface ServerOverviewProps {
  onRefresh?: () => void;
}

export function ServerOverview({ onRefresh }: ServerOverviewProps) {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDevices = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await deviceApi.list();
        if (response.success && response.data?.items) {
          const devicesData = response.data.items;
          
          // Fetch container info for each device in parallel
          const devicesWithContainers = await Promise.all(
            devicesData.map(async (device: any) => {
              let containerInfo = null;
              try {
                const containerResponse = await containerApi.list(device.hostname);
                if (containerResponse.success && containerResponse.data?.containers) {
                  const containers = containerResponse.data.containers;
                  containerInfo = {
                    total: containers.length,
                    running: containers.filter((c: any) => c.state === 'running').length,
                  };
                }
              } catch (containerError) {
                console.warn(`Failed to fetch containers for ${device.hostname}:`, containerError);
              }
              
              return {
                id: device.id,
                hostname: device.hostname,
                ip_address: device.ip_address,
                device_type: device.device_type,
                status: device.status,
                monitoring_enabled: device.monitoring_enabled,
                last_seen: device.last_seen,
                containers: containerInfo,
              };
            })
          );
          
          setDevices(devicesWithContainers);
        } else {
          throw new Error('Invalid response from devices API');
        }
      } catch (apiError: any) {
        console.error('Failed to fetch devices:', apiError);
        setError(apiError.message || 'Failed to fetch devices');
      } finally {
        setLoading(false);
      }
    };

    fetchDevices();
  }, []);

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 GB';
    const gb = bytes / (1024 ** 3);
    return gb > 1000 ? `${(gb / 1024).toFixed(2)} TB` : `${gb.toFixed(2)} GB`;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'online':
        return <CheckCircle className="h-3 w-3 text-green-500" />;
      case 'offline':
        return <AlertCircle className="h-3 w-3 text-red-500" />;
      default:
        return <AlertCircle className="h-3 w-3 text-yellow-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online':
        return 'text-green-400';
      case 'offline':
        return 'text-red-400';
      default:
        return 'text-yellow-400';
    }
  };

  if (loading) {
    return (
      <Card className="bg-gray-900 border-gray-800 h-full">
        <CardHeader className="pb-3">
          <CardTitle className="text-gray-400 text-xs uppercase tracking-wider">
            Servers (Loading...)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-3">
            <div className="h-20 bg-gray-800 rounded"></div>
            <div className="h-20 bg-gray-800 rounded"></div>
            <div className="h-20 bg-gray-800 rounded"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-gray-900 border-gray-800 h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-gray-400 text-xs uppercase tracking-wider">
            Servers ({devices.length})
            {error && (
              <span className="text-yellow-400 ml-2">(Partial data)</span>
            )}
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {devices.map((device) => (
          <div key={device.id} className="border border-gray-700 rounded-lg p-4 bg-gray-800/50">
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="text-gray-100 font-medium">{device.hostname}</h3>
                  {getStatusIcon(device.status)}
                </div>
                <p className="text-gray-400 text-xs">
                  {device.ip_address || 'No IP'} • {device.device_type}
                </p>
                <p className={`text-xs ${getStatusColor(device.status)}`}>
                  {device.status}
                </p>
              </div>
            </div>

            <div className="space-y-2">
              {device.containers && (
                <div className="flex items-center gap-2 text-gray-300">
                  <Package className="h-4 w-4 text-gray-500" />
                  <span className="text-sm">
                    {device.containers.running} / {device.containers.total} containers
                  </span>
                  {device.containers.running > 0 && (
                    <Badge 
                      variant="ghost" 
                      className="h-4 px-1 text-xs bg-transparent text-green-400 border-0"
                    >
                      Running
                    </Badge>
                  )}
                </div>
              )}
              
              <div className="flex items-center gap-2 text-gray-300">
                <Server className="h-4 w-4 text-gray-500" />
                <span className="text-sm">
                  Monitoring: {device.monitoring_enabled ? 'Enabled' : 'Disabled'}
                </span>
              </div>
            </div>
          </div>
        ))}

        {/* Add Server Button */}
        <button className="w-full border border-gray-700 border-dashed rounded-lg p-3 text-gray-400 hover:text-gray-300 hover:border-gray-600 transition-colors text-sm">
          + Add Server
        </button>
      </CardContent>
    </Card>
  );
}
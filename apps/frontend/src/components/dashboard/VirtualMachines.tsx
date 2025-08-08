import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Package, HardDrive, AlertTriangle } from 'lucide-react';
import { useEffect, useState } from 'react';
import { containerApi } from '@/services/api';
import type { APIResponse } from '@infrastructor/shared-types';

interface Container {
  id: string;
  name: string;
  status?: 'running' | 'exited' | 'stopped' | 'paused' | string;
  state?: string;
  image?: string;
  ports?: unknown[];
  created_at?: string;
  started_at?: string;
  finished_at?: string;
}

interface VirtualMachinesProps {
  deviceHostname?: string;
}

export function VirtualMachines({ deviceHostname = 'tootie' }: VirtualMachinesProps) {
  const [containers, setContainers] = useState<Container[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchContainers = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = (await containerApi.list(deviceHostname)) as APIResponse<{ containers: Container[] }>;
        if (response.success && response.data && 'containers' in response.data) {
          const containerData = (response.data as { containers: Container[] }).containers.slice(0, 10); // Limit to first 10 containers
          setContainers(containerData);
        } else {
          throw new Error('Invalid response from containers API');
        }
      } catch (apiError: unknown) {
        const err = apiError as Error;
        console.error('Failed to fetch containers:', err);
        setError(err.message || 'Failed to fetch container information');
        
        // Show some fallback data
        setContainers([
          {
            id: '1',
            name: 'nginx-proxy',
            status: 'running',
            state: 'running',
            image: 'nginx:latest'
          },
          {
            id: '2', 
            name: 'redis-cache',
            status: 'running',
            state: 'running',
            image: 'redis:alpine'
          }
        ]);
      } finally {
        setLoading(false);
      }
    };

    fetchContainers();
  }, [deviceHostname]);

  const getStatusColor = (status?: string) => {
    const s = (status ?? '').toLowerCase();
    switch (s) {
      case 'running':
        return 'bg-green-500';
      case 'exited':
      case 'stopped':
        return 'bg-red-500';
      case 'paused':
        return 'bg-yellow-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusBadgeColor = (status?: string) => {
    const s = (status ?? '').toLowerCase();
    switch (s) {
      case 'running':
        return 'bg-green-900/50 text-green-300';
      case 'exited':
      case 'stopped':
        return 'bg-red-900/50 text-red-300';
      case 'paused':
        return 'bg-yellow-900/50 text-yellow-300';
      default:
        return 'bg-gray-900/50 text-gray-300';
    }
  };

  if (loading) {
    return (
      <Card className="bg-gray-900 border-gray-800">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-gray-100">
            <Package className="h-4 w-4" />
            Containers (Loading...)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-3">
            <div className="h-16 bg-gray-800 rounded"></div>
            <div className="h-16 bg-gray-800 rounded"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-gray-900 border-gray-800">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-gray-100">
          <Package className="h-4 w-4" />
          Containers ({containers.length})
          {error && (
            <div className="flex items-center gap-1 text-yellow-400">
              <AlertTriangle className="h-3 w-3" />
              <span className="text-xs">Fallback data</span>
            </div>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {containers.map((container) => (
          <div key={container.id} className="border border-gray-700 rounded-lg p-3 bg-gray-800/30">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-3">
                <div className={`w-2 h-2 rounded-full ${getStatusColor(container.status ?? container.state)}`} />
                <h4 className="text-gray-100 font-medium text-sm">{container.name}</h4>
                <Badge 
                  variant="secondary" 
                  className={`text-xs px-2 py-0 ${getStatusBadgeColor(container.status ?? container.state)}`}
                >
                  {container.status ?? container.state ?? 'unknown'}
                </Badge>
              </div>
            </div>
            
            <div className="flex items-center gap-4 text-sm">
              {container.image && (
                <div className="flex items-center gap-2">
                  <Package className="h-3 w-3 text-gray-400" />
                  <Badge 
                    variant="secondary" 
                    className="bg-blue-900/50 text-blue-300 text-xs px-1.5 py-0 h-5"
                  >
                    {container.image.split(':')[0]}
                  </Badge>
                  {container.image.includes(':') && (
                    <Badge 
                      variant="secondary" 
                      className="bg-gray-900/50 text-gray-300 text-xs px-1.5 py-0 h-5"
                    >
                      {container.image.split(':')[1]}
                    </Badge>
                  )}
                </div>
              )}
              
              {container.ports && container.ports.length > 0 && (
                <div className="flex items-center gap-2">
                  <HardDrive className="h-3 w-3 text-gray-400" />
                  <Badge 
                    variant="secondary" 
                    className="bg-purple-900/50 text-purple-300 text-xs px-1.5 py-0 h-5"
                  >
                    {container.ports.length} port{container.ports.length !== 1 ? 's' : ''}
                  </Badge>
                </div>
              )}
            </div>
          </div>
        ))}
        
        {containers.length === 0 && !loading && (
          <div className="text-center py-8 text-gray-400">
            <Package className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>No containers found</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
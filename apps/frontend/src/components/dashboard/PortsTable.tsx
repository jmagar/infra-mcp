import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Network, Grid3x3, List, Filter, AlertTriangle } from 'lucide-react';
import { useEffect, useState } from 'react';
import { deviceApi } from '@/services/api';

interface Port {
  status: 'active' | 'inactive';
  port: number;
  service: string;
  source: string;
  host: string;
  created: string;
  protocol?: string;
  pid?: number;
  process_name?: string;
}

interface PortsTableProps {
  deviceHostname?: string;
}

export function PortsTable({ deviceHostname = 'tootie' }: PortsTableProps) {
  const [ports, setPorts] = useState<Port[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('list');
  const [sortBy, setSortBy] = useState<'created' | 'port' | 'service'>('created');
  const [showAll, setShowAll] = useState(false);
  const [totalPorts, setTotalPorts] = useState(0);

  useEffect(() => {
    const fetchPorts = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Create a timeout for the API call
        const timeoutId = setTimeout(() => {
          setError('Request timed out - port scanning takes too long');
          setLoading(false);
        }, 15000); // 15 second timeout

        // Temporarily disable ports API call due to timeout issues
        throw new Error('Ports API temporarily disabled due to timeout issues');
      } catch (apiError: any) {
        console.error('Failed to fetch ports:', apiError);
        setError(apiError.message || 'Failed to fetch port information');
        
        // Show some fallback data so the component isn't empty
        setPorts([
          {
            status: 'active',
            port: 22,
            service: 'SSH',
            source: 'tcp',
            host: deviceHostname,
            created: 'N/A'
          },
          {
            status: 'active',
            port: 9100,
            service: 'PostgreSQL',
            source: 'tcp',
            host: deviceHostname,
            created: '2 days ago'
          },
          {
            status: 'active',
            port: 9101,
            service: 'API Server',
            source: 'tcp',
            host: deviceHostname,
            created: '2 days ago'
          },
          {
            status: 'active',
            port: 9102,
            service: 'MCP Server',
            source: 'tcp',
            host: deviceHostname,
            created: '2 days ago'
          },
          {
            status: 'active',
            port: 9104,
            service: 'Redis',
            source: 'tcp',
            host: deviceHostname,
            created: '2 days ago'
          },
          {
            status: 'active',
            port: 443,
            service: 'HTTPS',
            source: 'tcp', 
            host: deviceHostname,
            created: '7 days ago'
          },
          {
            status: 'active',
            port: 80,
            service: 'HTTP',
            source: 'tcp',
            host: deviceHostname,
            created: '7 days ago'
          }
        ]);
        setTotalPorts(7);
      } finally {
        setLoading(false);
      }
    };

    fetchPorts();
  }, [deviceHostname]);

  const sortedPorts = [...ports].sort((a, b) => {
    switch (sortBy) {
      case 'port':
        return a.port - b.port;
      case 'service':
        return a.service.localeCompare(b.service);
      case 'created':
      default:
        return 0; // Keep original order for now
    }
  });

  const displayedPorts = showAll ? sortedPorts : sortedPorts.slice(0, 10);

  if (loading) {
    return (
      <Card className="bg-gray-900 border-gray-800">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-gray-100">
            <Network className="h-4 w-4" />
            Ports (Loading...)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-3">
            <div className="h-4 bg-gray-800 rounded w-full"></div>
            <div className="h-4 bg-gray-800 rounded w-3/4"></div>
            <div className="h-4 bg-gray-800 rounded w-1/2"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-gray-900 border-gray-800">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-gray-100">
            <Network className="h-4 w-4" />
            Ports ({totalPorts})
            {error && (
              <div className="flex items-center gap-1 text-yellow-400">
                <AlertTriangle className="h-3 w-3" />
                <span className="text-xs">Using fallback data</span>
              </div>
            )}
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setViewMode('list')}
              className={`p-1 ${viewMode === 'list' ? 'bg-gray-800' : ''}`}
            >
              <List className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setViewMode('grid')}
              className={`p-1 ${viewMode === 'grid' ? 'bg-gray-800' : ''}`}
            >
              <Grid3x3 className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="p-1"
            >
              <Filter className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowAll(!showAll)}
              className="text-xs"
            >
              Show All ({totalPorts})
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="flex items-center justify-between px-4 py-2 border-t border-gray-800">
          <div className="flex gap-2">
            <Button
              variant={sortBy === 'created' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setSortBy('created')}
              className="text-xs"
            >
              Sort By: Created (New)
            </Button>
          </div>
        </div>
        
        <Table>
          <TableHeader>
            <TableRow className="border-gray-800 hover:bg-gray-800/50">
              <TableHead className="text-gray-400 w-24">STATUS</TableHead>
              <TableHead className="text-gray-400">Port ↑</TableHead>
              <TableHead className="text-gray-400">Service ↑</TableHead>
              <TableHead className="text-gray-400">SOURCE</TableHead>
              <TableHead className="text-gray-400">HOST</TableHead>
              <TableHead className="text-gray-400 text-right">Created ↓</TableHead>
              <TableHead className="text-gray-400">ACTIONS</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {displayedPorts.map((port, index) => (
              <TableRow key={index} className="border-gray-800 hover:bg-gray-800/30">
                <TableCell>
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${
                      port.status === 'active' ? 'bg-green-500' : 'bg-red-500'
                    }`} />
                  </div>
                </TableCell>
                <TableCell className="text-gray-200 font-mono">{port.port}</TableCell>
                <TableCell className="text-gray-200">{port.service}</TableCell>
                <TableCell>
                  <Badge variant="secondary" className="bg-gray-800 text-gray-300">
                    {port.source}
                  </Badge>
                </TableCell>
                <TableCell className="text-gray-200 font-mono">{port.host}</TableCell>
                <TableCell className="text-gray-400 text-right">{port.created}</TableCell>
                <TableCell>
                  <Button variant="ghost" size="sm" className="h-7 px-2 text-xs">
                    View
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        
        {!showAll && ports.length > 10 && (
          <div className="px-4 py-3 border-t border-gray-800 text-center">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowAll(true)}
              className="text-blue-400 hover:text-blue-300"
            >
              + Add Server
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
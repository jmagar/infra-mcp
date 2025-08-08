/**
 * VM Logs Viewer
 * Interface for viewing libvirt and VM-specific logs
 */

import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useVMLogs } from '@/hooks/useVMLogs';
import { useResponsive } from '@/hooks/useResponsive';
import {
  Monitor,
  RefreshCw,
  Search,
  Download,
  AlertTriangle,
  Clock,
  Play,
  Pause,
  Terminal,
} from 'lucide-react';

interface VMLogsViewerProps {
  hostname?: string;
}

export function VMLogsViewer({ hostname: propHostname }: VMLogsViewerProps) {
  const { hostname: paramHostname } = useParams<{ hostname: string }>();
  const hostname = propHostname || paramHostname;
  const { isMobile } = useResponsive();
  
  const {
    logs,
    vmLogs,
    availableVMs,
    loading,
    error,
    refetch,
    getVMSpecificLogs,
  } = useVMLogs(hostname);

  const [searchTerm, setSearchTerm] = useState('');
  const [selectedVM, setSelectedVM] = useState<string>('');
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState<NodeJS.Timeout | null>(null);

  // Auto-refresh functionality
  useEffect(() => {
    if (autoRefresh && hostname) {
      const interval = setInterval(() => {
        refetch();
        if (selectedVM) {
          getVMSpecificLogs(selectedVM);
        }
      }, 10000); // Refresh every 10 seconds
      
      setRefreshInterval(interval);
      return () => clearInterval(interval);
    } else if (refreshInterval) {
      clearInterval(refreshInterval);
      setRefreshInterval(null);
    }
  }, [autoRefresh, hostname, selectedVM, refetch, getVMSpecificLogs, refreshInterval]);

  if (!hostname) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">No hostname provided</p>
      </div>
    );
  }

  const filterLogs = (logContent: string, search: string): string => {
    if (!search.trim()) return logContent;
    
    const lines = logContent.split('\n');
    const filtered = lines.filter(line =>
      line.toLowerCase().includes(search.toLowerCase())
    );
    
    return filtered.join('\n');
  };

  const highlightSearchTerm = (text: string, term: string): string => {
    if (!term.trim()) return text;
    
    const regex = new RegExp(`(${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    return text.replace(regex, '<mark class="bg-yellow-200 dark:bg-yellow-800">$1</mark>');
  };

  const downloadLogs = (content: string, filename: string) => {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const formatLogContent = (content: string): string => {
    // Add basic formatting for common log patterns
    return content
      .replace(/(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})/g, '<span class="text-blue-600 font-mono">$1</span>')
      .replace(/\[ERROR\]/gi, '<span class="text-red-600 font-bold">[ERROR]</span>')
      .replace(/\[WARN\]/gi, '<span class="text-yellow-600 font-bold">[WARN]</span>')
      .replace(/\[INFO\]/gi, '<span class="text-green-600 font-bold">[INFO]</span>')
      .replace(/\[DEBUG\]/gi, '<span class="text-gray-600 font-bold">[DEBUG]</span>');
  };

  return (
    <div className="space-y-6 p-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">VM Logs</h1>
          <p className="text-muted-foreground">
            View libvirt and VM-specific logs on {hostname}
          </p>
        </div>
        <div className="flex space-x-2">
          <Button
            variant={autoRefresh ? "default" : "outline"}
            onClick={() => setAutoRefresh(!autoRefresh)}
            disabled={loading}
          >
            {autoRefresh ? <Pause className="h-4 w-4 mr-2" /> : <Play className="h-4 w-4 mr-2" />}
            {autoRefresh ? 'Stop' : 'Auto Refresh'}
          </Button>
          <Button variant="outline" onClick={refetch} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            {!isMobile && 'Refresh'}
          </Button>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="h-4 w-4 text-red-600" />
              <span className="text-red-800">{error}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Search Controls */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Search className="h-5 w-5" />
            <span>Log Search & Filters</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-4">
            <div className="flex-1">
              <Input
                placeholder="Search logs..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full"
              />
            </div>
            <div className="flex space-x-2">
              {availableVMs && availableVMs.length > 0 && (
                <select
                  value={selectedVM}
                  onChange={(e) => {
                    setSelectedVM(e.target.value);
                    if (e.target.value) {
                      getVMSpecificLogs(e.target.value);
                    }
                  }}
                  className="px-3 py-2 border border-input rounded-md bg-background"
                >
                  <option value="">Select VM...</option>
                  {availableVMs.map((vm) => (
                    <option key={vm} value={vm}>
                      {vm}
                    </option>
                  ))}
                </select>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="libvirt" className="space-y-4">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="libvirt" className="flex items-center space-x-2">
            <Terminal className="h-4 w-4" />
            <span>Libvirt Logs</span>
          </TabsTrigger>
          <TabsTrigger value="vm-specific" className="flex items-center space-x-2">
            <Monitor className="h-4 w-4" />
            <span>VM-Specific Logs</span>
            {selectedVM && (
              <Badge variant="secondary" className="ml-2">
                {selectedVM}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="libvirt">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center space-x-2">
                <Terminal className="h-5 w-5" />
                <span>Libvirt Daemon Logs</span>
                {logs?.success && (
                  <Badge variant="default">
                    <Clock className="h-3 w-3 mr-1" />
                    Live
                  </Badge>
                )}
              </CardTitle>
              <div className="flex space-x-2">
                {logs?.logs && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => downloadLogs(logs.logs, `libvirt-logs-${hostname}-${new Date().toISOString().slice(0, 19)}.txt`)}
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Download
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center h-64">
                  <div className="text-center">
                    <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-2" />
                    <p className="text-muted-foreground">Loading libvirt logs...</p>
                  </div>
                </div>
              ) : logs ? (
                <div className="space-y-4">
                  {/* Log Info */}
                  <div className="flex items-center justify-between text-sm text-muted-foreground">
                    <span>Source: {logs.log_source}</span>
                    <span>Lines: {logs.logs.split('\n').length}</span>
                  </div>
                  
                  {/* Log Content */}
                  <div className="bg-black text-green-400 p-4 rounded-lg font-mono text-sm overflow-auto max-h-96">
                    <pre
                      className="whitespace-pre-wrap"
                      dangerouslySetInnerHTML={{
                        __html: highlightSearchTerm(
                          formatLogContent(filterLogs(logs.logs, searchTerm)),
                          searchTerm
                        ),
                      }}
                    />
                  </div>
                  
                  {searchTerm && (
                    <div className="text-sm text-muted-foreground">
                      Showing filtered results for: <strong>"{searchTerm}"</strong>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center h-64 flex items-center justify-center">
                  <p className="text-muted-foreground">No libvirt logs available</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="vm-specific">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center space-x-2">
                <Monitor className="h-5 w-5" />
                <span>VM-Specific Logs</span>
                {selectedVM && vmLogs?.[selectedVM]?.success && (
                  <Badge variant="default">
                    <Clock className="h-3 w-3 mr-1" />
                    Live
                  </Badge>
                )}
              </CardTitle>
              <div className="flex space-x-2">
                {selectedVM && vmLogs?.[selectedVM]?.logs && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => downloadLogs(
                      vmLogs[selectedVM].logs, 
                      `vm-logs-${selectedVM}-${hostname}-${new Date().toISOString().slice(0, 19)}.txt`
                    )}
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Download
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {!selectedVM ? (
                <div className="text-center h-64 flex items-center justify-center">
                  <div>
                    <Monitor className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <p className="text-muted-foreground">Select a VM to view its logs</p>
                  </div>
                </div>
              ) : loading ? (
                <div className="flex items-center justify-center h-64">
                  <div className="text-center">
                    <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-2" />
                    <p className="text-muted-foreground">Loading VM logs for {selectedVM}...</p>
                  </div>
                </div>
              ) : vmLogs?.[selectedVM] ? (
                <div className="space-y-4">
                  {/* Log Info */}
                  <div className="flex items-center justify-between text-sm text-muted-foreground">
                    <span>VM: {selectedVM}</span>
                    <span>Source: {vmLogs[selectedVM].log_source}</span>
                    <span>Lines: {vmLogs[selectedVM].logs.split('\n').length}</span>
                  </div>
                  
                  {/* Log Content */}
                  <div className="bg-black text-green-400 p-4 rounded-lg font-mono text-sm overflow-auto max-h-96">
                    <pre
                      className="whitespace-pre-wrap"
                      dangerouslySetInnerHTML={{
                        __html: highlightSearchTerm(
                          formatLogContent(filterLogs(vmLogs[selectedVM].logs, searchTerm)),
                          searchTerm
                        ),
                      }}
                    />
                  </div>
                  
                  {searchTerm && (
                    <div className="text-sm text-muted-foreground">
                      Showing filtered results for: <strong>"{searchTerm}"</strong>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center h-64 flex items-center justify-center">
                  <p className="text-muted-foreground">No logs available for {selectedVM}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useContainer, useContainers } from '@/hooks/useContainers';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useResponsive } from '@/hooks/useResponsive';
import { useNotificationEvents } from '@/hooks/useNotificationEvents';
import { StatusBadge, MetricCard, LoadingSpinner } from '@/components/common';
import { gridConfigs, spacing, typography, layout } from '@/lib/responsive';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import {
  ArrowLeft as ArrowLeftIcon,
  Play as PlayIcon,
  Pause as PauseIcon,
  RotateCw as ArrowPathIcon,
  Trash2 as TrashIcon,
  Terminal as CommandLineIcon,
  FileText as DocumentTextIcon,
  BarChart3 as ChartBarIcon,
  Info as InformationCircleIcon,
  RefreshCw as RefreshCwIcon,
  Copy as CopyIcon,
} from 'lucide-react';
import type { ContainerResponse } from '@infrastructor/shared-types';

export function ContainerDetails() {
  const { device, containerName } = useParams<{ device: string; containerName: string }>();
  const navigate = useNavigate();
  const { isMobile, isTablet } = useResponsive();
  const { container, loading, error } = useContainer(device, containerName);
  const { startContainer, stopContainer, restartContainer, removeContainer, getContainerLogs } = useContainers(device);
  const { data: liveMetrics } = useWebSocket(`ws://localhost:9101/ws/container-metrics/${device}/${containerName}`);
  const { notifyContainerAction, notifyError } = useNotificationEvents({ device, container: containerName });
  
  const [activeTab, setActiveTab] = useState('overview');
  const [logs, setLogs] = useState<string[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [terminalCommand, setTerminalCommand] = useState('');
  const [terminalOutput, setTerminalOutput] = useState<string[]>([]);
  const [following, setFollowing] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (activeTab === 'logs' && device && containerName) {
      fetchLogs();
    }
  }, [activeTab, device, containerName]);

  useEffect(() => {
    if (following && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, following]);

  const fetchLogs = async (tail = 100) => {
    if (!device || !containerName) return;
    
    setLogsLoading(true);
    try {
      const containerLogs = await getContainerLogs(device, containerName, { tail });
      setLogs(containerLogs.split('\n').filter(line => line.trim()));
    } catch (error) {
      console.error('Failed to fetch logs:', error);
      setLogs(['Error fetching logs: ' + error.message]);
    } finally {
      setLogsLoading(false);
    }
  };

  const handleContainerAction = async (action: 'start' | 'stop' | 'restart' | 'remove') => {
    if (!device || !containerName) return;

    try {
      switch (action) {
        case 'start':
          await startContainer(device, containerName);
          notifyContainerAction('start', containerName, device, true);
          break;
        case 'stop':
          await stopContainer(device, containerName);
          notifyContainerAction('stop', containerName, device, true);
          break;
        case 'restart':
          await restartContainer(device, containerName);
          notifyContainerAction('restart', containerName, device, true);
          break;
        case 'remove':
          if (confirm(`Are you sure you want to remove container "${containerName}"?`)) {
            await removeContainer(device, containerName);
            notifyContainerAction('remove', containerName, device, true);
            navigate('/containers');
          }
          return;
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error(`Failed to ${action} container:`, error);
      notifyContainerAction(action, containerName, device, false, errorMessage);
    }
  };

  const executeCommand = async () => {
    if (!terminalCommand.trim()) return;

    // This would integrate with a real terminal/exec API
    const newOutput = `$ ${terminalCommand}`;
    setTerminalOutput(prev => [...prev, newOutput]);
    
    // Mock response - in real implementation, this would call an exec API
    setTimeout(() => {
      setTerminalOutput(prev => [...prev, `Mock response for: ${terminalCommand}`]);
    }, 500);
    
    setTerminalCommand('');
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  if (loading) {
    return (
      <div className={`${spacing.padding.page} ${layout.sectionWrapper}`}>
        <LoadingSpinner size="lg" text="Loading container details..." />
      </div>
    );
  }

  if (error || !container) {
    return (
      <div className={`${spacing.padding.page} ${layout.sectionWrapper}`}>
        <div className="text-center">
          <h1 className={typography.heading.page}>Container Not Found</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Container "{containerName}" on device "{device}" could not be found.
          </p>
          <Button onClick={() => navigate('/containers')} className="mt-4">
            <ArrowLeftIcon className="h-4 w-4 mr-2" />
            Back to Containers
          </Button>
        </div>
      </div>
    );
  }

  const metrics = liveMetrics || container;
  const isRunning = container.status === 'running';

  return (
    <div className={`${spacing.padding.page} ${layout.sectionWrapper}`}>
      {/* Header */}
      <div className={layout.pageHeader.full}>
        <div className="flex items-center space-x-3">
          <Button variant="ghost" onClick={() => navigate('/containers')}>
            <ArrowLeftIcon className="h-4 w-4" />
          </Button>
          <div>
            <h1 className={typography.heading.page}>{container.name}</h1>
            <p className={`${typography.body.normal} text-gray-600 dark:text-gray-400`}>
              Container on {device} • {container.image}
            </p>
          </div>
        </div>
        <div className={layout.navButtons.full}>
          <Button variant="outline" onClick={() => window.location.reload()} size={isMobile ? "sm" : "default"}>
            <RefreshCwIcon className="h-4 w-4 mr-2" />
            {!isMobile && "Refresh"}
          </Button>
          
          {isRunning ? (
            <Button 
              onClick={() => handleContainerAction('stop')} 
              variant="outline"
              size={isMobile ? "sm" : "default"}
            >
              <PauseIcon className="h-4 w-4 mr-2" />
              {isMobile ? "Stop" : "Stop Container"}
            </Button>
          ) : (
            <Button 
              onClick={() => handleContainerAction('start')} 
              size={isMobile ? "sm" : "default"}
            >
              <PlayIcon className="h-4 w-4 mr-2" />
              {isMobile ? "Start" : "Start Container"}
            </Button>
          )}
        </div>
      </div>

      {/* Quick Stats */}
      <div className={`${gridConfigs.dashboardMetrics.full} ${spacing.gap.full}`}>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Status</CardTitle>
            <InformationCircleIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <StatusBadge status={container.status} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">CPU Usage</CardTitle>
            <ChartBarIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {typeof metrics.cpu_usage === 'number' ? `${metrics.cpu_usage.toFixed(1)}%` : '--'}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Memory Usage</CardTitle>
            <ChartBarIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {typeof metrics.memory_usage === 'number' ? `${metrics.memory_usage.toFixed(1)}%` : '--'}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Ports</CardTitle>
            <InformationCircleIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {container.ports?.length || 0}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Card>
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <CardHeader>
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="overview">
                <InformationCircleIcon className="h-4 w-4 mr-2" />
                {!isMobile && "Overview"}
              </TabsTrigger>
              <TabsTrigger value="logs">
                <DocumentTextIcon className="h-4 w-4 mr-2" />
                {!isMobile && "Logs"}
              </TabsTrigger>
              <TabsTrigger value="stats">
                <ChartBarIcon className="h-4 w-4 mr-2" />
                {!isMobile && "Stats"}
              </TabsTrigger>
              <TabsTrigger value="terminal" disabled={!isRunning}>
                <CommandLineIcon className="h-4 w-4 mr-2" />
                {!isMobile && "Terminal"}
              </TabsTrigger>
            </TabsList>
          </CardHeader>

          <CardContent>
            <TabsContent value="overview" className="space-y-4">
              <div className={`${gridConfigs.detailPanels.full} ${spacing.gap.full}`}>
                {/* Container Info */}
                <Card>
                  <CardHeader>
                    <CardTitle>Container Information</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">Name:</span>
                      <span className="text-sm font-medium">{container.name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">Image:</span>
                      <span className="text-sm font-medium break-all">{container.image}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">Status:</span>
                      <StatusBadge status={container.status} />
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">Created:</span>
                      <span className="text-sm font-medium">
                        {container.created_at ? new Date(container.created_at).toLocaleString() : 'Unknown'}
                      </span>
                    </div>
                    {container.restart_policy && (
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Restart Policy:</span>
                        <Badge variant="secondary">{container.restart_policy}</Badge>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Network & Ports */}
                <Card>
                  <CardHeader>
                    <CardTitle>Network & Ports</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {container.ports && container.ports.length > 0 ? (
                      <div className="space-y-2">
                        {container.ports.map((port, index) => (
                          <div key={index} className="flex justify-between items-center p-2 bg-gray-50 dark:bg-gray-800 rounded">
                            <span className="text-sm">
                              {port.host_port}:{port.container_port}
                            </span>
                            <div className="flex items-center space-x-2">
                              <Badge variant="outline">{port.protocol || 'tcp'}</Badge>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => copyToClipboard(`localhost:${port.host_port}`)}
                              >
                                <CopyIcon className="h-3 w-3" />
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-gray-500 dark:text-gray-400">No ports exposed</p>
                    )}
                  </CardContent>
                </Card>
              </div>

              {/* Actions */}
              <div className="flex flex-wrap gap-2">
                <Button onClick={() => handleContainerAction('restart')} variant="outline">
                  <ArrowPathIcon className="h-4 w-4 mr-2" />
                  Restart
                </Button>
                <Button 
                  onClick={() => handleContainerAction('remove')} 
                  variant="destructive"
                >
                  <TrashIcon className="h-4 w-4 mr-2" />
                  Remove
                </Button>
              </div>
            </TabsContent>

            <TabsContent value="logs" className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Button
                    onClick={() => fetchLogs(100)}
                    variant="outline"
                    size="sm"
                    disabled={logsLoading}
                  >
                    <RefreshCwIcon className="h-4 w-4 mr-2" />
                    Refresh
                  </Button>
                  <Button
                    onClick={() => setFollowing(!following)}
                    variant={following ? "default" : "outline"}
                    size="sm"
                  >
                    {following ? "Stop Follow" : "Follow"}
                  </Button>
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  {logs.length} lines
                </div>
              </div>

              <Card>
                <CardContent className="p-0">
                  <div className="bg-black text-green-400 font-mono text-sm p-4 h-96 overflow-y-auto">
                    {logsLoading ? (
                      <div className="flex items-center justify-center h-full">
                        <LoadingSpinner size="sm" text="Loading logs..." />
                      </div>
                    ) : (
                      <>
                        {logs.map((line, index) => (
                          <div key={index} className="mb-1 whitespace-pre-wrap break-all">
                            {line}
                          </div>
                        ))}
                        <div ref={logsEndRef} />
                      </>
                    )}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="stats" className="space-y-4">
              <div className={`${gridConfigs.detailPanels.full} ${spacing.gap.full}`}>
                <MetricCard
                  title="CPU Usage"
                  value={typeof metrics.cpu_usage === 'number' ? metrics.cpu_usage.toFixed(1) : '--'}
                  unit="%"
                  description="Current CPU utilization"
                  change={metrics.cpu_usage}
                  changeType={metrics.cpu_usage > 80 ? 'decrease' : 'increase'}
                />
                
                <MetricCard
                  title="Memory Usage"
                  value={typeof metrics.memory_usage === 'number' ? metrics.memory_usage.toFixed(1) : '--'}
                  unit="%"
                  description="Current memory utilization"
                  change={metrics.memory_usage}
                  changeType={metrics.memory_usage > 85 ? 'decrease' : 'increase'}
                />
              </div>
            </TabsContent>

            <TabsContent value="terminal" className="space-y-4">
              <Card>
                <CardContent className="p-0">
                  <div className="bg-black text-white font-mono text-sm">
                    <div className="p-4 h-64 overflow-y-auto">
                      {terminalOutput.map((line, index) => (
                        <div key={index} className="mb-1">
                          {line}
                        </div>
                      ))}
                    </div>
                    <div className="border-t border-gray-700 p-4">
                      <div className="flex items-center space-x-2">
                        <span className="text-green-400">$</span>
                        <Input
                          value={terminalCommand}
                          onChange={(e) => setTerminalCommand(e.target.value)}
                          onKeyPress={(e) => e.key === 'Enter' && executeCommand()}
                          placeholder="Enter command..."
                          className="bg-transparent border-none text-white placeholder-gray-400 focus:ring-0"
                        />
                        <Button onClick={executeCommand} size="sm">
                          Execute
                        </Button>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </CardContent>
        </Tabs>
      </Card>
    </div>
  );
}
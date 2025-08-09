/**
 * Real-Time Logs Viewer Component
 * Live log streaming with WebSocket integration, filtering, and search
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import {
  FileText,
  Search,
  Filter,
  Pause,
  Play,
  Download,
  Trash2,
  AlertTriangle,
  Info,
  XCircle,
  CheckCircle,
  Settings,
  ScrollText,
  Clock,
} from 'lucide-react';
import { useWebSocket } from '@/hooks';
import { cn } from '@/lib/design-system';

interface LogEntry {
  id: string;
  timestamp: string;
  level: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR' | 'CRITICAL';
  source: string; // device_id or service name
  hostname?: string;
  service?: string;
  message: string;
  metadata?: Record<string, any>;
}

type LogLevel = LogEntry['level'] | 'ALL';

interface RealTimeLogsViewerProps {
  deviceIds?: string[];
  services?: string[];
  maxLogs?: number;
  autoScroll?: boolean;
}

export function RealTimeLogsViewer({
  deviceIds = [],
  services = [],
  maxLogs = 500,
  autoScroll = true,
}: RealTimeLogsViewerProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filteredLogs, setFilteredLogs] = useState<LogEntry[]>([]);
  const [isPaused, setIsPaused] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLevel, setSelectedLevel] = useState<LogLevel>('ALL');
  const [selectedSource, setSelectedSource] = useState<string>('ALL');
  const [showTimestamps, setShowTimestamps] = useState(true);
  const [wordWrap, setWordWrap] = useState(true);
  const [highlightErrors, setHighlightErrors] = useState(true);
  
  const logsContainerRef = useRef<HTMLDivElement>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // WebSocket connection for log streaming
  const logStream = useWebSocket({
    url: `ws://localhost:9101/ws/logs`,
    onMessage: useCallback((message) => {
      if (message.type === 'log' && !isPaused) {
        const logEntry = message.data as LogEntry;
        
        setLogs(prev => {
          const newLogs = [...prev, { ...logEntry, id: `${Date.now()}-${Math.random()}` }];
          return newLogs.slice(-maxLogs);
        });
      }
    }, [isPaused, maxLogs]),
  });

  // Subscribe to log streams on connection
  useEffect(() => {
    if (logStream.isConnected) {
      // Subscribe to device logs
      deviceIds.forEach(deviceId => {
        logStream.subscribe('device_logs', { device_id: deviceId });
      });
      
      // Subscribe to service logs
      services.forEach(service => {
        logStream.subscribe('service_logs', { service });
      });
      
      // Subscribe to system logs
      logStream.subscribe('system_logs');
    }
  }, [logStream, logStream.isConnected, deviceIds, services]);

  // Filter logs based on search and level
  useEffect(() => {
    let filtered = logs;

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(log => 
        log.message.toLowerCase().includes(query) ||
        log.source.toLowerCase().includes(query) ||
        log.hostname?.toLowerCase().includes(query) ||
        log.service?.toLowerCase().includes(query)
      );
    }

    // Filter by level
    if (selectedLevel !== 'ALL') {
      filtered = filtered.filter(log => log.level === selectedLevel);
    }

    // Filter by source
    if (selectedSource !== 'ALL') {
      filtered = filtered.filter(log => 
        log.source === selectedSource ||
        log.hostname === selectedSource ||
        log.service === selectedSource
      );
    }

    setFilteredLogs(filtered);
  }, [logs, searchQuery, selectedLevel, selectedSource]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (autoScroll && !isPaused && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [filteredLogs, autoScroll, isPaused]);

  // Get unique sources for filtering
  const uniqueSources = React.useMemo(() => {
    const sources = new Set<string>();
    logs.forEach(log => {
      sources.add(log.source);
      if (log.hostname) sources.add(log.hostname);
      if (log.service) sources.add(log.service);
    });
    return Array.from(sources).sort();
  }, [logs]);

  const handlePauseToggle = () => {
    setIsPaused(!isPaused);
  };

  const handleClearLogs = () => {
    setLogs([]);
    setFilteredLogs([]);
  };

  const handleExportLogs = () => {
    const logsToExport = filteredLogs.length > 0 ? filteredLogs : logs;
    const content = logsToExport.map(log => 
      `${log.timestamp} [${log.level}] ${log.source}: ${log.message}`
    ).join('\n');

    const blob = new Blob([content], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `logs_${new Date().toISOString().slice(0, 19)}.txt`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const getLevelColor = (level: LogEntry['level']) => {
    switch (level) {
      case 'DEBUG': return 'text-gray-500';
      case 'INFO': return 'text-blue-600';
      case 'WARN': return 'text-yellow-600';
      case 'ERROR': return 'text-red-600';
      case 'CRITICAL': return 'text-red-800 font-bold';
      default: return 'text-gray-600';
    }
  };

  const getLevelIcon = (level: LogEntry['level']) => {
    switch (level) {
      case 'DEBUG': return Info;
      case 'INFO': return CheckCircle;
      case 'WARN': return AlertTriangle;
      case 'ERROR': return XCircle;
      case 'CRITICAL': return XCircle;
      default: return Info;
    }
  };

  const getLevelBadgeVariant = (level: LogEntry['level']): "default" | "secondary" | "destructive" | "outline" => {
    switch (level) {
      case 'ERROR':
      case 'CRITICAL':
        return 'destructive';
      case 'WARN':
        return 'outline';
      default:
        return 'secondary';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-3">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            <CardTitle>Real-Time Logs</CardTitle>
            {isPaused && <Badge variant="secondary">Paused</Badge>}
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <div className={cn(
                "w-2 h-2 rounded-full",
                logStream.isConnected ? "bg-green-500" : "bg-red-500"
              )} />
              <span>{logStream.isConnected ? 'Connected' : 'Disconnected'}</span>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handlePauseToggle}
            >
              {isPaused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={handleExportLogs}
              disabled={logs.length === 0}
            >
              <Download className="w-4 h-4" />
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={handleClearLogs}
              disabled={logs.length === 0}
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-2">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search logs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8"
              />
            </div>
          </div>
          
          <Select value={selectedLevel} onValueChange={(value) => setSelectedLevel(value as LogLevel)}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All Levels</SelectItem>
              <SelectItem value="DEBUG">Debug</SelectItem>
              <SelectItem value="INFO">Info</SelectItem>
              <SelectItem value="WARN">Warning</SelectItem>
              <SelectItem value="ERROR">Error</SelectItem>
              <SelectItem value="CRITICAL">Critical</SelectItem>
            </SelectContent>
          </Select>
          
          <Select value={selectedSource} onValueChange={setSelectedSource}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All Sources</SelectItem>
              {uniqueSources.map(source => (
                <SelectItem key={source} value={source}>{source}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Display Options */}
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="timestamps"
              checked={showTimestamps}
              onCheckedChange={setShowTimestamps}
            />
            <label htmlFor="timestamps" className="cursor-pointer">Show timestamps</label>
          </div>
          
          <div className="flex items-center space-x-2">
            <Checkbox
              id="wordwrap"
              checked={wordWrap}
              onCheckedChange={setWordWrap}
            />
            <label htmlFor="wordwrap" className="cursor-pointer">Word wrap</label>
          </div>
          
          <div className="flex items-center space-x-2">
            <Checkbox
              id="highlight"
              checked={highlightErrors}
              onCheckedChange={setHighlightErrors}
            />
            <label htmlFor="highlight" className="cursor-pointer">Highlight errors</label>
          </div>

          <div className="text-muted-foreground">
            {filteredLogs.length} of {logs.length} entries
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="flex-1 min-h-0">
        <div 
          ref={logsContainerRef}
          className="h-full overflow-auto bg-gray-900 text-gray-100 rounded-lg p-4 font-mono text-sm"
        >
          {filteredLogs.length === 0 ? (
            <div className="flex items-center justify-center h-full text-gray-400">
              <div className="text-center">
                <ScrollText className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>No logs available</p>
                <p className="text-xs">
                  {logs.length === 0 
                    ? 'Waiting for log entries...' 
                    : 'No logs match current filters'
                  }
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-1">
              {filteredLogs.map((log) => {
                const LevelIcon = getLevelIcon(log.level);
                const isError = log.level === 'ERROR' || log.level === 'CRITICAL';
                
                return (
                  <div
                    key={log.id}
                    className={cn(
                      "flex items-start gap-2 py-1 px-2 rounded text-xs hover:bg-gray-800/50",
                      highlightErrors && isError && "bg-red-900/20 border-l-2 border-l-red-500",
                      !wordWrap && "whitespace-nowrap overflow-hidden"
                    )}
                  >
                    <LevelIcon className={cn("w-3 h-3 mt-0.5 flex-shrink-0", getLevelColor(log.level))} />
                    
                    {showTimestamps && (
                      <span className="text-gray-400 flex-shrink-0 w-20">
                        {formatTimestamp(log.timestamp)}
                      </span>
                    )}
                    
                    <Badge variant={getLevelBadgeVariant(log.level)} className="text-xs px-1 py-0 flex-shrink-0">
                      {log.level}
                    </Badge>
                    
                    <span className="text-blue-400 flex-shrink-0 min-w-0">
                      [{log.hostname || log.service || log.source}]
                    </span>
                    
                    <span className={cn(
                      "flex-1 min-w-0",
                      wordWrap ? "break-words" : "truncate"
                    )}>
                      {log.message}
                    </span>
                  </div>
                );
              })}
              <div ref={logsEndRef} />
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
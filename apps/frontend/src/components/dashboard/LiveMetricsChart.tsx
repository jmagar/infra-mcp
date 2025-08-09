/**
 * Live Metrics Chart Component
 * Real-time data visualization with WebSocket integration
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import {
  Activity,
  MemoryStick,
  HardDrive,
  Wifi,
  Pause,
  Play,
  Download,
  TrendingUp,
  BarChart3,
} from 'lucide-react';
import { useMetricsStream } from '@/hooks';

interface MetricDataPoint {
  timestamp: string;
  time: string;
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_rx: number;
  network_tx: number;
  device_id: string;
  hostname: string;
}

type MetricType = 'cpu' | 'memory' | 'disk' | 'network';
type ChartType = 'line' | 'area';

interface LiveMetricsChartProps {
  deviceIds?: string[];
  maxDataPoints?: number;
  updateInterval?: number;
  autoScroll?: boolean;
}

export function LiveMetricsChart({
  deviceIds = [],
  maxDataPoints = 50,
  updateInterval = 5000,
  autoScroll = true,
}: LiveMetricsChartProps) {
  const [selectedMetric, setSelectedMetric] = useState<MetricType>('cpu');
  const [chartType, setChartType] = useState<ChartType>('line');
  const [isPaused, setIsPaused] = useState(false);
  const [dataHistory, setDataHistory] = useState<MetricDataPoint[]>([]);
  const [deviceColors, setDeviceColors] = useState<Record<string, string>>({});
  
  const metricsStream = useMetricsStream(deviceIds);
  const chartContainerRef = useRef<HTMLDivElement>(null);

  // Color palette for different devices
  const colorPalette = [
    '#3B82F6', '#EF4444', '#10B981', '#F59E0B', 
    '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16',
    '#F97316', '#6366F1', '#14B8A6', '#F472B6',
  ];

  // Assign colors to devices
  useEffect(() => {
    const newColors: Record<string, string> = {};
    deviceIds.forEach((deviceId, index) => {
      if (!deviceColors[deviceId]) {
        newColors[deviceId] = colorPalette[index % colorPalette.length];
      }
    });
    
    if (Object.keys(newColors).length > 0) {
      setDeviceColors(prev => ({ ...prev, ...newColors }));
    }
  }, [deviceIds, deviceColors, colorPalette]);

  // Process incoming WebSocket data
  useEffect(() => {
    if (isPaused) return;
    
    if (metricsStream.lastMessage?.type === 'metrics') {
      const data = metricsStream.lastMessage.data as any;
      const timestamp = new Date().toISOString();
      const time = new Date().toLocaleTimeString();
      
      const dataPoint: MetricDataPoint = {
        timestamp,
        time,
        cpu_usage: data.cpu_usage || 0,
        memory_usage: data.memory_usage || 0,
        disk_usage: data.disk_usage || 0,
        network_rx: (data.network_rx || 0) / 1024 / 1024, // Convert to MB/s
        network_tx: (data.network_tx || 0) / 1024 / 1024, // Convert to MB/s
        device_id: data.device_id || 'unknown',
        hostname: data.hostname || 'Unknown Device',
      };

      setDataHistory(prev => {
        const newData = [...prev, dataPoint];
        return newData.slice(-maxDataPoints);
      });
    }
  }, [metricsStream.lastMessage, isPaused, maxDataPoints]);

  // Auto-scroll to latest data
  useEffect(() => {
    if (autoScroll && chartContainerRef.current) {
      chartContainerRef.current.scrollLeft = chartContainerRef.current.scrollWidth;
    }
  }, [dataHistory, autoScroll]);

  // Get unique devices in current data
  const uniqueDevices = React.useMemo(() => {
    const devices = new Set(dataHistory.map(d => d.device_id));
    return Array.from(devices).map(deviceId => ({
      id: deviceId,
      hostname: dataHistory.find(d => d.device_id === deviceId)?.hostname || 'Unknown',
      color: deviceColors[deviceId] || '#6B7280',
    }));
  }, [dataHistory, deviceColors]);

  const handlePauseToggle = () => {
    setIsPaused(!isPaused);
  };

  const handleClearData = () => {
    setDataHistory([]);
  };

  const handleExportData = () => {
    const csvContent = [
      ['Timestamp', 'Device', 'CPU %', 'Memory %', 'Disk %', 'Network RX MB/s', 'Network TX MB/s'].join(','),
      ...dataHistory.map(d => 
        [d.timestamp, d.hostname, d.cpu_usage, d.memory_usage, d.disk_usage, d.network_rx.toFixed(2), d.network_tx.toFixed(2)].join(',')
      )
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `metrics_${new Date().toISOString().slice(0, 19)}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const getMetricConfig = (metric: MetricType) => {
    switch (metric) {
      case 'cpu':
        return {
          icon: Activity,
          title: 'CPU Usage',
          dataKey: 'cpu_usage',
          unit: '%',
          color: '#EF4444',
        };
      case 'memory':
        return {
          icon: MemoryStick,
          title: 'Memory Usage',
          dataKey: 'memory_usage',
          unit: '%',
          color: '#3B82F6',
        };
      case 'disk':
        return {
          icon: HardDrive,
          title: 'Disk Usage',
          dataKey: 'disk_usage',
          unit: '%',
          color: '#10B981',
        };
      case 'network':
        return {
          icon: Wifi,
          title: 'Network I/O',
          dataKey: ['network_rx', 'network_tx'],
          unit: 'MB/s',
          color: '#F59E0B',
        };
    }
  };

  const config = getMetricConfig(selectedMetric);
  const MetricIcon = config.icon;

  // Custom tooltip component
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || !payload.length) return null;

    return (
      <div className="bg-white border rounded-lg p-3 shadow-lg">
        <p className="text-sm font-medium mb-2">{label}</p>
        {payload.map((entry: any, index: number) => {
          const deviceInfo = uniqueDevices.find(d => d.id === entry.payload?.device_id);
          return (
            <div key={index} className="flex items-center gap-2 text-sm">
              <div 
                className="w-3 h-3 rounded-full" 
                style={{ backgroundColor: entry.color }} 
              />
              <span>{deviceInfo?.hostname || 'Unknown'}: </span>
              <span className="font-medium">
                {typeof entry.value === 'number' ? entry.value.toFixed(2) : entry.value}{config.unit}
              </span>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <CardTitle className="flex items-center gap-2">
            <MetricIcon className="w-5 h-5" />
            Live {config.title}
            {isPaused && <Badge variant="secondary">Paused</Badge>}
          </CardTitle>
          
          <div className="flex items-center gap-2">
            <Select value={selectedMetric} onValueChange={(value) => setSelectedMetric(value as MetricType)}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="cpu">CPU</SelectItem>
                <SelectItem value="memory">Memory</SelectItem>
                <SelectItem value="disk">Disk</SelectItem>
                <SelectItem value="network">Network</SelectItem>
              </SelectContent>
            </Select>
            
            <Select value={chartType} onValueChange={(value) => setChartType(value as ChartType)}>
              <SelectTrigger className="w-24">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="line">Line</SelectItem>
                <SelectItem value="area">Area</SelectItem>
              </SelectContent>
            </Select>
            
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
              onClick={handleExportData}
              disabled={dataHistory.length === 0}
            >
              <Download className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        <div className="space-y-4">
          {/* Connection Status */}
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${
                metricsStream.isConnected ? 'bg-green-500' : 'bg-red-500'
              }`} />
              <span className="text-muted-foreground">
                {metricsStream.isConnected ? 'Connected' : 'Disconnected'}
                {isPaused && ' (Paused)'}
              </span>
            </div>
            
            <div className="flex items-center gap-4">
              <span className="text-muted-foreground">
                Data Points: {dataHistory.length}/{maxDataPoints}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleClearData}
                disabled={dataHistory.length === 0}
              >
                Clear
              </Button>
            </div>
          </div>

          {/* Device Legend */}
          {uniqueDevices.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {uniqueDevices.map(device => (
                <div key={device.id} className="flex items-center gap-2 text-sm">
                  <div 
                    className="w-3 h-3 rounded-full" 
                    style={{ backgroundColor: device.color }}
                  />
                  <span>{device.hostname}</span>
                </div>
              ))}
            </div>
          )}

          {/* Chart */}
          <div className="h-80" ref={chartContainerRef}>
            {dataHistory.length === 0 ? (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                <div className="text-center">
                  <BarChart3 className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p>No data available</p>
                  <p className="text-sm">
                    {metricsStream.isConnected 
                      ? 'Waiting for metrics data...' 
                      : 'Connect to start receiving data'
                    }
                  </p>
                </div>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                {chartType === 'area' ? (
                  <AreaChart data={dataHistory}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="time" 
                      tick={{ fontSize: 12 }}
                      interval="preserveStartEnd"
                    />
                    <YAxis 
                      tick={{ fontSize: 12 }}
                      domain={selectedMetric === 'network' ? ['auto', 'auto'] : [0, 100]}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend />
                    
                    {selectedMetric === 'network' ? (
                      <>
                        {uniqueDevices.map(device => (
                          <React.Fragment key={device.id}>
                            <Area
                              type="monotone"
                              dataKey={`network_rx`}
                              stroke={device.color}
                              fill={`${device.color}20`}
                              strokeWidth={2}
                              name={`${device.hostname} RX`}
                              data={dataHistory.filter(d => d.device_id === device.id)}
                            />
                            <Area
                              type="monotone"
                              dataKey={`network_tx`}
                              stroke={device.color}
                              fill={`${device.color}40`}
                              strokeWidth={2}
                              strokeDasharray="5 5"
                              name={`${device.hostname} TX`}
                              data={dataHistory.filter(d => d.device_id === device.id)}
                            />
                          </React.Fragment>
                        ))}
                      </>
                    ) : (
                      uniqueDevices.map(device => (
                        <Area
                          key={device.id}
                          type="monotone"
                          dataKey={config.dataKey as string}
                          stroke={device.color}
                          fill={`${device.color}20`}
                          strokeWidth={2}
                          name={device.hostname}
                          data={dataHistory.filter(d => d.device_id === device.id)}
                        />
                      ))
                    )}
                  </AreaChart>
                ) : (
                  <LineChart data={dataHistory}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="time" 
                      tick={{ fontSize: 12 }}
                      interval="preserveStartEnd"
                    />
                    <YAxis 
                      tick={{ fontSize: 12 }}
                      domain={selectedMetric === 'network' ? ['auto', 'auto'] : [0, 100]}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend />
                    
                    {selectedMetric === 'network' ? (
                      <>
                        {uniqueDevices.map(device => (
                          <React.Fragment key={device.id}>
                            <Line
                              type="monotone"
                              dataKey={`network_rx`}
                              stroke={device.color}
                              strokeWidth={2}
                              dot={false}
                              name={`${device.hostname} RX`}
                              data={dataHistory.filter(d => d.device_id === device.id)}
                            />
                            <Line
                              type="monotone"
                              dataKey={`network_tx`}
                              stroke={device.color}
                              strokeWidth={2}
                              strokeDasharray="5 5"
                              dot={false}
                              name={`${device.hostname} TX`}
                              data={dataHistory.filter(d => d.device_id === device.id)}
                            />
                          </React.Fragment>
                        ))}
                      </>
                    ) : (
                      uniqueDevices.map(device => (
                        <Line
                          key={device.id}
                          type="monotone"
                          dataKey={config.dataKey as string}
                          stroke={device.color}
                          strokeWidth={2}
                          dot={false}
                          name={device.hostname}
                          data={dataHistory.filter(d => d.device_id === device.id)}
                        />
                      ))
                    )}
                  </LineChart>
                )}
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
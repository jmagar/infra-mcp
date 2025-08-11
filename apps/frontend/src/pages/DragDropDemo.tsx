import * as React from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { DragDropContainers } from "@/components/management/DragDropContainers"
import { DragDropDevices } from "@/components/management/DragDropDevices"
import { Shuffle, RefreshCw } from "lucide-react"

// Mock data for demonstration
const mockContainers = [
  {
    id: "cont-1",
    name: "nginx-proxy",
    image: "nginx:alpine",
    status: "Up 2 hours",
    state: "running",
    ports: [{ private: 80, public: 8080, type: "tcp" }, { private: 443, public: 8443, type: "tcp" }],
    deviceId: "device-1"
  },
  {
    id: "cont-2", 
    name: "postgres-db",
    image: "postgres:15",
    status: "Up 1 day",
    state: "running",
    ports: [{ private: 5432, public: 5432, type: "tcp" }],
    deviceId: "device-1"
  },
  {
    id: "cont-3",
    name: "redis-cache",
    image: "redis:7-alpine", 
    status: "Exited (0) 5 minutes ago",
    state: "exited",
    ports: [{ private: 6379, type: "tcp" }],
    deviceId: "device-2"
  },
  {
    id: "cont-4",
    name: "app-backend",
    image: "node:18-alpine",
    status: "Up 30 minutes",
    state: "running", 
    ports: [{ private: 3000, public: 3000, type: "tcp" }],
    deviceId: undefined // Unassigned
  },
  {
    id: "cont-5",
    name: "monitoring",
    image: "grafana/grafana:latest",
    status: "Created",
    state: "created",
    ports: [{ private: 3000, public: 3001, type: "tcp" }],
    deviceId: undefined // Unassigned
  }
];

const mockDevices = [
  {
    id: "device-1",
    hostname: "web-server-01",
    ip_address: "192.168.1.10",
    status: "online" as const,
    device_type: "server",
    location: "Data Center A",
    tags: { environment: "production", role: "web" },
    containers: 2,
    services: 5,
    last_seen: new Date().toISOString(),
    metrics: { cpu: 45, memory: 72, disk: 38, uptime: "2d 14h 32m" }
  },
  {
    id: "device-2", 
    hostname: "app-server-01",
    ip_address: "192.168.1.11",
    status: "online" as const,
    device_type: "server", 
    location: "Data Center A",
    tags: { environment: "production", role: "app" },
    containers: 1,
    services: 3,
    last_seen: new Date().toISOString(),
    metrics: { cpu: 23, memory: 54, disk: 67, uptime: "1d 8h 15m" }
  },
  {
    id: "device-3",
    hostname: "db-server-01", 
    ip_address: "192.168.1.12",
    status: "warning" as const,
    device_type: "database",
    location: "Data Center B",
    tags: { environment: "production", role: "database" },
    containers: 0,
    services: 2,
    last_seen: new Date(Date.now() - 300000).toISOString(), // 5 minutes ago
    metrics: { cpu: 78, memory: 89, disk: 45, uptime: "5d 2h 43m" },
    groupId: "group-1"
  },
  {
    id: "device-4",
    hostname: "staging-01",
    ip_address: "192.168.1.20",
    status: "offline" as const,
    device_type: "server",
    location: "Data Center B", 
    tags: { environment: "staging", role: "testing" },
    containers: 0,
    services: 0,
    last_seen: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
    groupId: "group-2"
  }
];

const mockDeviceGroups = [
  {
    id: "group-1",
    name: "Production Database",
    description: "High-performance database servers",
    color: "blue",
    devices: mockDevices.filter(d => d.groupId === "group-1")
  },
  {
    id: "group-2", 
    name: "Staging Environment",
    description: "Testing and development servers",
    color: "green",
    devices: mockDevices.filter(d => d.groupId === "group-2")
  },
  {
    id: "group-3",
    name: "Edge Nodes",
    description: "Distributed edge computing nodes", 
    color: "purple",
    devices: []
  }
];

const mockDeviceZones = [
  {
    id: "device-1",
    hostname: "web-server-01", 
    status: "online" as const,
    containers: mockContainers.filter(c => c.deviceId === "device-1")
  },
  {
    id: "device-2",
    hostname: "app-server-01",
    status: "online" as const, 
    containers: mockContainers.filter(c => c.deviceId === "device-2")
  },
  {
    id: "device-3",
    hostname: "db-server-01",
    status: "warning" as const,
    containers: []
  }
];

export function DragDropDemo() {
  // Container Management State
  const [containers, setContainers] = React.useState(mockContainers);
  const [deviceZones, setDeviceZones] = React.useState(mockDeviceZones); 
  const [selectedContainers, setSelectedContainers] = React.useState<string[]>([]);

  // Device Management State
  const [devices, setDevices] = React.useState(mockDevices);
  const [deviceGroups, setDeviceGroups] = React.useState(mockDeviceGroups);
  const [selectedDevices, setSelectedDevices] = React.useState<string[]>([]);

  // Container Management Handlers
  const handleContainerAction = (action: string, containerIds: string[]) => {
    console.log(`Container action: ${action}`, containerIds);
    // Simulate state changes for demo
    if (action === 'start') {
      setContainers(prev => prev.map(c => 
        containerIds.includes(c.id) 
          ? { ...c, status: "Up just now", state: "running" }
          : c
      ));
    } else if (action === 'stop') {
      setContainers(prev => prev.map(c =>
        containerIds.includes(c.id)
          ? { ...c, status: "Exited (0) just now", state: "exited" }
          : c
      ));
    }
  };

  const handleContainerMove = (containerId: string, targetDeviceId: string) => {
    setContainers(prev => prev.map(c =>
      c.id === containerId ? { ...c, deviceId: targetDeviceId } : c
    ));
    
    // Update device zones
    setDeviceZones(prev => prev.map(zone => ({
      ...zone,
      containers: containers.filter(c => c.deviceId === zone.id)
    })));
  };

  const handleContainerReorder = (deviceId: string, reorderedContainers: any[]) => {
    console.log(`Reorder containers in device ${deviceId}:`, reorderedContainers);
  };

  // Device Management Handlers
  const handleDeviceAction = (action: string, deviceIds: string[]) => {
    console.log(`Device action: ${action}`, deviceIds);
  };

  const handleDeviceMove = (deviceId: string, targetGroupId: string | null) => {
    setDevices(prev => prev.map(d =>
      d.id === deviceId ? { ...d, groupId: targetGroupId } : d
    ));
    
    // Update device groups
    setDeviceGroups(prev => prev.map(group => ({
      ...group,
      devices: devices.filter(d => d.groupId === group.id)
    })));
  };

  const handleDeviceReorder = (groupId: string | null, reorderedDevices: any[]) => {
    console.log(`Reorder devices in group ${groupId}:`, reorderedDevices);
  };

  const handleGroupReorder = (reorderedGroups: any[]) => {
    setDeviceGroups(reorderedGroups);
  };

  const resetDemo = () => {
    setContainers(mockContainers);
    setDeviceZones(mockDeviceZones);
    setSelectedContainers([]);
    setDevices(mockDevices);
    setDeviceGroups(mockDeviceGroups);
    setSelectedDevices([]);
  };

  const shuffleItems = () => {
    // Randomly assign containers to devices
    const shuffledContainers = containers.map(c => ({
      ...c,
      deviceId: Math.random() > 0.7 ? undefined : `device-${Math.ceil(Math.random() * 3)}`
    }));
    setContainers(shuffledContainers);

    // Randomly assign devices to groups  
    const shuffledDevices = devices.map(d => ({
      ...d,
      groupId: Math.random() > 0.6 ? `group-${Math.ceil(Math.random() * 3)}` : undefined
    }));
    setDevices(shuffledDevices);
  };

  return (
    <div className="container max-w-7xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Drag & Drop Management</h1>
          <p className="text-muted-foreground">
            Interactive drag-and-drop interfaces for container and device management
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={shuffleItems}
            className="gap-2"
          >
            <Shuffle className="h-4 w-4" />
            Shuffle
          </Button>
          <Button
            variant="outline"
            onClick={resetDemo}
            className="gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Reset Demo
          </Button>
        </div>
      </div>

      {/* Demo Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Containers</CardDescription>
            <CardTitle className="text-2xl">{containers.length}</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="flex gap-1">
              <Badge variant="secondary" className="text-xs">
                {containers.filter(c => c.state === 'running').length} running
              </Badge>
              <Badge variant="outline" className="text-xs">
                {containers.filter(c => !c.deviceId).length} unassigned
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Devices</CardDescription>
            <CardTitle className="text-2xl">{devices.length}</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="flex gap-1">
              <Badge variant="secondary" className="text-xs">
                {devices.filter(d => d.status === 'online').length} online
              </Badge>
              <Badge variant="outline" className="text-xs">
                {devices.filter(d => !d.groupId).length} ungrouped
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Selected Items</CardDescription>
            <CardTitle className="text-2xl">
              {selectedContainers.length + selectedDevices.length}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="flex gap-1">
              {selectedContainers.length > 0 && (
                <Badge variant="secondary" className="text-xs">
                  {selectedContainers.length} containers
                </Badge>
              )}
              {selectedDevices.length > 0 && (
                <Badge variant="secondary" className="text-xs">
                  {selectedDevices.length} devices
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Device Groups</CardDescription>
            <CardTitle className="text-2xl">{deviceGroups.length}</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="flex gap-1">
              <Badge variant="secondary" className="text-xs">
                {deviceGroups.reduce((sum, g) => sum + g.devices.length, 0)} assigned
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Drag & Drop Interfaces */}
      <Tabs defaultValue="containers" className="space-y-4">
        <TabsList className="grid grid-cols-2 w-[400px]">
          <TabsTrigger value="containers">Container Management</TabsTrigger>
          <TabsTrigger value="devices">Device Management</TabsTrigger>
        </TabsList>

        <TabsContent value="containers" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                Container Drag & Drop Management
              </CardTitle>
              <CardDescription>
                Drag containers between devices, reorder within devices, and perform bulk actions.
                Try selecting multiple containers and dragging them around!
              </CardDescription>
            </CardHeader>
            <CardContent className="p-6">
              <DragDropContainers
                containers={containers}
                devices={deviceZones}
                selectedContainers={selectedContainers}
                onContainerAction={handleContainerAction}
                onContainerMove={handleContainerMove}
                onContainerReorder={handleContainerReorder}
                onSelectionChange={setSelectedContainers}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="devices" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                Device Drag & Drop Management
              </CardTitle>
              <CardDescription>
                Organize devices into groups, reorder within groups, and perform bulk operations.
                Groups can be reordered by dragging the entire group sections!
              </CardDescription>
            </CardHeader>
            <CardContent className="p-6">
              <DragDropDevices
                devices={devices}
                groups={deviceGroups}
                selectedDevices={selectedDevices}
                onDeviceAction={handleDeviceAction}
                onDeviceMove={handleDeviceMove}
                onDeviceReorder={handleDeviceReorder}
                onGroupReorder={handleGroupReorder}
                onSelectionChange={setSelectedDevices}
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
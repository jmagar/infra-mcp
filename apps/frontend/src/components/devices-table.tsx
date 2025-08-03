"use client"

import { useState } from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { MoreHorizontal, Server, Activity, AlertCircle } from "lucide-react"

interface Device {
  id: string
  hostname: string
  ip_address: string
  device_type: string
  status: "online" | "offline" | "maintenance"
  last_seen: string
  location?: string
  containers: number
}

const mockDevices: Device[] = [
  {
    id: "1",
    hostname: "server-01",
    ip_address: "192.168.1.10",
    device_type: "server",
    status: "online",
    last_seen: "2 minutes ago",
    location: "Rack A1",
    containers: 12,
  },
  {
    id: "2",
    hostname: "server-02",
    ip_address: "192.168.1.11",
    device_type: "server",
    status: "online",
    last_seen: "1 minute ago",
    location: "Rack A2",
    containers: 18,
  },
  {
    id: "3",
    hostname: "nas-01",
    ip_address: "192.168.1.20",
    device_type: "storage",
    status: "online",
    last_seen: "30 seconds ago",
    location: "Rack B1",
    containers: 8,
  },
  {
    id: "4",
    hostname: "backup-01",
    ip_address: "192.168.1.30",
    device_type: "backup",
    status: "maintenance",
    last_seen: "1 hour ago",
    location: "Rack C1",
    containers: 3,
  },
  {
    id: "5",
    hostname: "proxy-01",
    ip_address: "192.168.1.5",
    device_type: "proxy",
    status: "offline",
    last_seen: "2 hours ago",
    location: "DMZ",
    containers: 0,
  },
]

export function DevicesTable() {
  const [devices] = useState<Device[]>(mockDevices)

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "online":
        return <Activity className="h-4 w-4 text-green-500" />
      case "offline":
        return <AlertCircle className="h-4 w-4 text-red-500" />
      case "maintenance":
        return <AlertCircle className="h-4 w-4 text-yellow-500" />
      default:
        return <Server className="h-4 w-4 text-gray-500" />
    }
  }

  const getStatusVariant = (status: string) => {
    switch (status) {
      case "online":
        return "secondary"
      case "offline":
        return "destructive"
      case "maintenance":
        return "outline"
      default:
        return "outline"
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Server className="h-5 w-5" />
          <span>Infrastructure Devices</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Device</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Location</TableHead>
              <TableHead>Containers</TableHead>
              <TableHead>Last Seen</TableHead>
              <TableHead className="w-[50px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {devices.map((device) => (
              <TableRow key={device.id}>
                <TableCell>
                  <div className="flex items-center space-x-3">
                    {getStatusIcon(device.status)}
                    <div>
                      <div className="font-medium">{device.hostname}</div>
                      <div className="text-sm text-muted-foreground">{device.ip_address}</div>
                    </div>
                  </div>
                </TableCell>
                <TableCell>
                  <Badge variant="outline" className="capitalize">
                    {device.device_type}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge variant={getStatusVariant(device.status)} className="capitalize">
                    {device.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-muted-foreground">{device.location || "Unknown"}</TableCell>
                <TableCell>
                  <Badge variant="secondary">{device.containers}</Badge>
                </TableCell>
                <TableCell className="text-muted-foreground">{device.last_seen}</TableCell>
                <TableCell>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem>View Details</DropdownMenuItem>
                      <DropdownMenuItem>View Metrics</DropdownMenuItem>
                      <DropdownMenuItem>Manage Containers</DropdownMenuItem>
                      <DropdownMenuItem>View Logs</DropdownMenuItem>
                      <DropdownMenuItem>SSH Connect</DropdownMenuItem>
                      <DropdownMenuItem className="text-destructive">Remove Device</DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

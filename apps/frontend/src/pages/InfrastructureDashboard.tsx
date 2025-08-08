import { useState } from 'react';
import { ServerOverview } from '@/components/dashboard/ServerOverview';
import { SystemInformation } from '@/components/dashboard/SystemInformation';
import { VirtualMachines } from '@/components/dashboard/VirtualMachines';
import { PortsTable } from '@/components/dashboard/PortsTable';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Bell, Search, Settings, User, ChevronDown, RefreshCw, Home } from 'lucide-react';

export function InfrastructureDashboard() {
  const [selectedDevice, setSelectedDevice] = useState('tootie');
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Top Navigation Bar */}
      <div className="bg-gray-900 border-b border-gray-800">
        <div className="flex items-center justify-between px-4 py-2">
          {/* Left side - Logo and navigation */}
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">PT</span>
              </div>
              <span className="text-gray-100 font-semibold">porttracker</span>
            </div>
            
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                type="text"
                placeholder="Search ports, processes..."
                className="pl-10 pr-4 py-1.5 w-80 bg-gray-800 border-gray-700 text-gray-100 placeholder-gray-500"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>

          {/* Right side - Actions */}
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" className="text-gray-400 hover:text-gray-100">
              Docker
            </Button>
            <Button variant="ghost" size="sm" className="text-gray-400 hover:text-gray-100">
              System
            </Button>
            <Button 
              variant="ghost" 
              size="sm" 
              className="text-gray-400 hover:text-gray-100 gap-1"
            >
              <RefreshCw className="h-4 w-4" />
              Auto-refresh
            </Button>
            <div className="h-6 w-px bg-gray-700" />
            <Button variant="ghost" size="icon" className="text-gray-400 hover:text-gray-100">
              <Bell className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" className="text-gray-400 hover:text-gray-100">
              <Settings className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" className="text-gray-400 hover:text-gray-100">
              <User className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Breadcrumb */}
      <div className="bg-gray-900 px-4 py-2 border-b border-gray-800">
        <div className="flex items-center gap-2 text-sm">
          <Home className="h-4 w-4 text-gray-400" />
          <span className="text-gray-400">/</span>
          <span className="text-gray-100">Dashboard</span>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex">
        {/* Left Sidebar - Server Overview */}
        <div className="w-80 bg-gray-900 border-r border-gray-800 min-h-screen p-4">
          <ServerOverview hostname={selectedDevice} />
        </div>

        {/* Main Content Area */}
        <div className="flex-1 p-6">
          {/* Header with device selector */}
          <div className="mb-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <h1 className="text-2xl font-semibold text-gray-100">{selectedDevice}</h1>
                <Badge className="bg-green-900/30 text-green-400 border-green-800">
                  Online
                </Badge>
                <span className="text-gray-400 text-sm">192.168.1.100:4999</span>
              </div>
              <Button 
                variant="outline" 
                size="sm"
                className="border-gray-700 text-gray-300 hover:bg-gray-800"
              >
                <ChevronDown className="h-4 w-4 mr-2" />
                Switch Device
              </Button>
            </div>
          </div>

          {/* Dashboard Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* System Information */}
            <div>
              <SystemInformation deviceHostname={selectedDevice} />
            </div>

            {/* Virtual Machines */}
            <div>
              <VirtualMachines deviceHostname={selectedDevice} />
            </div>

            {/* Ports Table - Full Width */}
            <div className="lg:col-span-2">
              <PortsTable deviceHostname={selectedDevice} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


import * as React from "react"
import { Server, MapPin, Tag, Settings, Trash2, AlertTriangle, CheckCircle, Clock, Network } from "lucide-react"
import { cn } from "@/lib/design-system"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { StatusBadge } from "@/components/ui/status-badge"
import { 
  DragDropProvider, 
  Draggable, 
  DropZone, 
  SortableList, 
  BulkActions,
  useDragDrop 
} from "@/components/ui/drag-drop"

// Device interfaces
interface DeviceItem {
  id: string;
  hostname: string;
  ip_address: string;
  status: 'online' | 'offline' | 'warning';
  device_type: string;
  location?: string;
  description?: string;
  tags?: Record<string, string>;
  groupId?: string;
  metrics?: {
    cpu: number;
    memory: number;
    disk: number;
    uptime: string;
  };
  containers?: number;
  services?: number;
  last_seen: string;
}

interface DeviceGroup {
  id: string;
  name: string;
  description?: string;
  color: string;
  devices: DeviceItem[];
}

interface DeviceManagementProps {
  devices: DeviceItem[];
  groups: DeviceGroup[];
  selectedDevices: string[];
  onDeviceAction: (action: string, deviceIds: string[]) => void;
  onDeviceMove: (deviceId: string, targetGroupId: string | null) => void;
  onDeviceReorder: (groupId: string | null, reorderedDevices: DeviceItem[]) => void;
  onGroupReorder: (reorderedGroups: DeviceGroup[]) => void;
  onSelectionChange: (selectedIds: string[]) => void;
  className?: string;
}

// Device Card Component
function DeviceCard({ 
  device, 
  isSelected = false, 
  onSelect, 
  onAction,
  showMetrics = true 
}: {
  device: DeviceItem;
  isSelected?: boolean;
  onSelect?: (id: string, selected: boolean) => void;
  onAction?: (action: string, deviceId: string) => void;
  showMetrics?: boolean;
}) {
  const handleCheckboxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.stopPropagation();
    onSelect?.(device.id, e.target.checked);
  };

  const getStatusIcon = () => {
    switch (device.status) {
      case 'online':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'offline':
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      default:
        return <Clock className="h-4 w-4 text-muted-foreground" />;
    }
  };

  return (
    <div className={cn(
      "relative p-4 space-y-3",
      isSelected && "ring-2 ring-primary ring-offset-2"
    )}>
      {/* Selection Checkbox */}
      <div className="absolute top-2 left-2 z-10">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={handleCheckboxChange}
          className="h-4 w-4 rounded border-border text-primary focus:ring-2 focus:ring-primary focus:ring-offset-2"
        />
      </div>

      {/* Device Header */}
      <div className="flex items-start justify-between pl-6">
        <div className="space-y-1 flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <Server className="h-4 w-4 text-primary shrink-0" />
            <h3 className="font-semibold text-sm truncate">{device.hostname}</h3>
          </div>
          <div className="flex items-center gap-2">
            <Network className="h-3 w-3 text-muted-foreground shrink-0" />
            <p className="text-xs text-muted-foreground font-mono truncate">
              {device.ip_address}
            </p>
          </div>
          {device.location && (
            <div className="flex items-center gap-2">
              <MapPin className="h-3 w-3 text-muted-foreground shrink-0" />
              <p className="text-xs text-muted-foreground truncate">
                {device.location}
              </p>
            </div>
          )}
        </div>
        <div className="flex flex-col items-end gap-1">
          <StatusBadge 
            status={device.status} 
            size="sm"
            pulse={device.status === 'online'}
          >
            {device.status.charAt(0).toUpperCase() + device.status.slice(1)}
          </StatusBadge>
          <Badge variant="outline" className="text-xs">
            {device.device_type}
          </Badge>
        </div>
      </div>

      {/* Metrics */}
      {showMetrics && device.metrics && (
        <div className="grid grid-cols-3 gap-2 pl-6 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">CPU:</span>
            <span className="font-mono tabular-nums">{device.metrics.cpu}%</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">RAM:</span>
            <span className="font-mono tabular-nums">{device.metrics.memory}%</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Disk:</span>
            <span className="font-mono tabular-nums">{device.metrics.disk}%</span>
          </div>
        </div>
      )}

      {/* Services Summary */}
      <div className="flex items-center gap-4 pl-6 text-xs text-muted-foreground">
        <div className="flex items-center gap-1">
          <span>{device.containers || 0} containers</span>
        </div>
        <div className="flex items-center gap-1">
          <span>{device.services || 0} services</span>
        </div>
      </div>

      {/* Tags */}
      {device.tags && Object.keys(device.tags).length > 0 && (
        <div className="flex flex-wrap gap-1 pl-6">
          {Object.entries(device.tags).slice(0, 3).map(([key, value]) => (
            <Badge key={key} variant="secondary" className="text-xs">
              <Tag className="h-2 w-2 mr-1" />
              {key}: {value}
            </Badge>
          ))}
          {Object.keys(device.tags).length > 3 && (
            <Badge variant="secondary" className="text-xs">
              +{Object.keys(device.tags).length - 3} more
            </Badge>
          )}
        </div>
      )}

      {/* Quick Actions */}
      <div className="flex items-center justify-end gap-1 pl-6">
        <Button
          size="sm"
          variant="ghost"
          onClick={(e) => {
            e.stopPropagation();
            onAction?.('manage', device.id);
          }}
          className="h-7 w-7 p-0"
        >
          <Settings className="h-3 w-3" />
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={(e) => {
            e.stopPropagation();
            onAction?.('analyze', device.id);
          }}
          className="h-7 w-7 p-0"
        >
          {getStatusIcon()}
        </Button>
      </div>

      {/* Last Seen */}
      <div className="pl-6 text-xs text-muted-foreground">
        Last seen: {new Date(device.last_seen).toLocaleString()}
      </div>
    </div>
  );
}

// Device Group Component
function DeviceGroupZone({ 
  group, 
  selectedDevices,
  onDeviceSelect,
  onDeviceAction,
  onDeviceReorder 
}: {
  group: DeviceGroup;
  selectedDevices: string[];
  onDeviceSelect: (id: string, selected: boolean) => void;
  onDeviceAction: (action: string, deviceId: string) => void;
  onDeviceReorder: (reorderedDevices: DeviceItem[]) => void;
}) {
  const { isDragging, draggedItem } = useDragDrop();
  const canAcceptDevice = draggedItem?.type === 'device' && draggedItem?.data?.groupId !== group.id;

  const onlineCount = group.devices.filter(d => d.status === 'online').length;
  const offlineCount = group.devices.filter(d => d.status === 'offline').length;
  const warningCount = group.devices.filter(d => d.status === 'warning').length;

  return (
    <div className="space-y-4">
      {/* Group Header */}
      <div className={cn(
        "flex items-center justify-between p-4 glass rounded-lg border-l-4",
        `border-l-${group.color}-500`
      )}>
        <div className="flex items-center gap-3">
          <div className={cn(
            "h-8 w-8 rounded-full flex items-center justify-center",
            `bg-${group.color}-100 dark:bg-${group.color}-900/20`
          )}>
            <Server className={cn(
              "h-4 w-4",
              `text-${group.color}-600 dark:text-${group.color}-400`
            )} />
          </div>
          <div>
            <h3 className="font-semibold">{group.name}</h3>
            <p className="text-sm text-muted-foreground">
              {group.devices.length} devices
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {onlineCount > 0 && (
            <Badge variant="secondary" className="text-xs bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-300">
              {onlineCount} online
            </Badge>
          )}
          {warningCount > 0 && (
            <Badge variant="secondary" className="text-xs bg-yellow-100 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-300">
              {warningCount} warning
            </Badge>
          )}
          {offlineCount > 0 && (
            <Badge variant="secondary" className="text-xs bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-300">
              {offlineCount} offline
            </Badge>
          )}
        </div>
      </div>

      {/* Device Drop Zone for Empty Groups */}
      {group.devices.length === 0 && (
        <DropZone
          dropId={`group-${group.id}`}
          dropType="device"
          emptyMessage="No devices - drop devices here to organize"
          dragOverMessage="Add device to this group"
          className="min-h-32"
        />
      )}

      {/* Devices List */}
      {group.devices.length > 0 && (
        <div className="space-y-2">
          <SortableList
            items={group.devices}
            onReorder={onDeviceReorder}
            renderItem={(device) => (
              <Draggable
                dragId={device.id}
                dragType="device"
                dragData={{ ...device, groupId: group.id }}
                variant="card"
                className="hover:shadow-md"
              >
                <DeviceCard
                  device={device}
                  isSelected={selectedDevices.includes(device.id)}
                  onSelect={onDeviceSelect}
                  onAction={onDeviceAction}
                />
              </Draggable>
            )}
            itemKey={(device) => device.id}
            gap="sm"
          />

          {/* Additional Drop Zone for Non-Empty Groups */}
          <DropZone
            dropId={`group-${group.id}-add`}
            dropType="device"
            canDrop={(draggedItem) => draggedItem.data?.groupId !== group.id}
            size="sm"
            emptyMessage="Drop devices here to add to group"
            className={cn(
              "border-dashed border-border/20",
              !canAcceptDevice && isDragging && "hidden"
            )}
          />
        </div>
      )}
    </div>
  );
}

// Ungrouped Devices Component
function UngroupedDevices({ 
  devices,
  selectedDevices,
  onDeviceSelect,
  onDeviceAction,
  onDeviceReorder 
}: {
  devices: DeviceItem[];
  selectedDevices: string[];
  onDeviceSelect: (id: string, selected: boolean) => void;
  onDeviceAction: (action: string, deviceId: string) => void;
  onDeviceReorder: (reorderedDevices: DeviceItem[]) => void;
}) {
  if (devices.length === 0) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Server className="h-5 w-5 text-muted-foreground" />
        <h2 className="text-lg font-semibold">Ungrouped Devices</h2>
        <Badge variant="secondary" className="ml-2">
          {devices.length}
        </Badge>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {devices.map(device => (
          <Draggable
            key={device.id}
            dragId={device.id}
            dragType="device"
            dragData={device}
            variant="card"
            className="glass border border-border/50 hover:shadow-lg"
          >
            <DeviceCard
              device={device}
              isSelected={selectedDevices.includes(device.id)}
              onSelect={onDeviceSelect}
              onAction={onDeviceAction}
            />
          </Draggable>
        ))}
      </div>
    </div>
  );
}

// Main Device Management Component
export function DragDropDevices({
  devices,
  groups,
  selectedDevices,
  onDeviceAction,
  onDeviceMove,
  onDeviceReorder,
  onGroupReorder,
  onSelectionChange,
  className
}: DeviceManagementProps) {
  const handleDrop = (draggedItem: any, targetId: string, targetType: string) => {
    if (draggedItem.type === 'device') {
      const groupId = targetId.replace('group-', '').replace('-add', '');
      const targetGroupId = groupId === 'ungrouped' ? null : groupId;
      
      if (draggedItem.data.groupId !== targetGroupId) {
        onDeviceMove(draggedItem.data.id, targetGroupId);
      }
    }
  };

  const handleDeviceSelect = (id: string, selected: boolean) => {
    const newSelection = selected
      ? [...selectedDevices, id]
      : selectedDevices.filter(did => did !== id);
    onSelectionChange(newSelection);
  };

  const handleBulkAction = (action: string) => {
    if (selectedDevices.length > 0) {
      onDeviceAction(action, selectedDevices);
    }
  };

  const clearSelection = () => {
    onSelectionChange([]);
  };

  const ungroupedDevices = devices.filter(device => !device.groupId);

  return (
    <DragDropProvider onDrop={handleDrop}>
      <div className={cn("space-y-6", className)}>
        {/* Ungrouped Devices */}
        <UngroupedDevices
          devices={ungroupedDevices}
          selectedDevices={selectedDevices}
          onDeviceSelect={handleDeviceSelect}
          onDeviceAction={onDeviceAction}
          onDeviceReorder={(reordered) => onDeviceReorder(null, reordered)}
        />

        {/* Device Groups */}
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Tag className="h-5 w-5 text-primary" />
              <h2 className="text-lg font-semibold">Device Groups</h2>
              <Badge variant="secondary" className="ml-2">
                {groups.length}
              </Badge>
            </div>
          </div>

          <SortableList
            items={groups}
            onReorder={onGroupReorder}
            renderItem={(group) => (
              <DeviceGroupZone
                group={group}
                selectedDevices={selectedDevices}
                onDeviceSelect={handleDeviceSelect}
                onDeviceAction={onDeviceAction}
                onDeviceReorder={(reordered) => onDeviceReorder(group.id, reordered)}
              />
            )}
            itemKey={(group) => group.id}
            gap="lg"
            className="space-y-6"
          />
        </div>

        {/* Bulk Actions Toolbar */}
        <BulkActions
          selectedItems={selectedDevices}
          onClearSelection={clearSelection}
        >
          <Button
            size="sm"
            variant="secondary"
            onClick={() => handleBulkAction('analyze')}
            className="gap-2"
          >
            <CheckCircle className="h-3 w-3" />
            Analyze All
          </Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => handleBulkAction('manage')}
            className="gap-2"
          >
            <Settings className="h-3 w-3" />
            Manage All
          </Button>
          <Button
            size="sm"
            variant="destructive"
            onClick={() => handleBulkAction('remove')}
            className="gap-2"
          >
            <Trash2 className="h-3 w-3" />
            Remove All
          </Button>
        </BulkActions>
      </div>
    </DragDropProvider>
  );
}
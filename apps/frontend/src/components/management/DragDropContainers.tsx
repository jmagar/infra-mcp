import * as React from "react"
import { Container, Server, Move, Archive, Trash2, Play, Square, RotateCcw, Package } from "lucide-react"
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

// Container interfaces
interface ContainerItem {
  id: string;
  name: string;
  image: string;
  status: string;
  state: string;
  ports: Array<{ private: number; public?: number; type: string }>;
  deviceId?: string;
}

interface DeviceZone {
  id: string;
  hostname: string;
  status: 'online' | 'offline' | 'warning';
  containers: ContainerItem[];
}

interface ContainerManagementProps {
  containers: ContainerItem[];
  devices: DeviceZone[];
  selectedContainers: string[];
  onContainerAction: (action: string, containerIds: string[]) => void;
  onContainerMove: (containerId: string, targetDeviceId: string) => void;
  onContainerReorder: (deviceId: string, reorderedContainers: ContainerItem[]) => void;
  onSelectionChange: (selectedIds: string[]) => void;
  className?: string;
}

// Container Card Component
function ContainerCard({ 
  container, 
  isSelected = false, 
  onSelect, 
  onAction 
}: {
  container: ContainerItem;
  isSelected?: boolean;
  onSelect?: (id: string, selected: boolean) => void;
  onAction?: (action: string, containerId: string) => void;
}) {
  const getStatusVariant = (status: string) => {
    if (status.includes('Up') || status === 'running') return 'running';
    if (status.includes('Exited')) return 'stopped';
    if (status === 'created') return 'pending';
    return 'unknown';
  };

  const handleCheckboxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.stopPropagation();
    onSelect?.(container.id, e.target.checked);
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

      {/* Container Header */}
      <div className="flex items-start justify-between pl-6">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Container className="h-4 w-4 text-blue-500" />
            <h3 className="font-semibold text-sm truncate">{container.name}</h3>
          </div>
          <p className="text-xs text-muted-foreground font-mono truncate">
            {container.image}
          </p>
        </div>
        <StatusBadge 
          status={getStatusVariant(container.status)} 
          size="sm"
          pulse={getStatusVariant(container.status) === 'running'}
        >
          {container.status}
        </StatusBadge>
      </div>

      {/* Ports */}
      {container.ports.length > 0 && (
        <div className="flex flex-wrap gap-1 pl-6">
          {container.ports.slice(0, 3).map((port, index) => (
            <Badge key={index} variant="outline" className="text-xs">
              {port.public ? `${port.public}:${port.private}` : port.private}
            </Badge>
          ))}
          {container.ports.length > 3 && (
            <Badge variant="outline" className="text-xs">
              +{container.ports.length - 3} more
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
            onAction?.('logs', container.id);
          }}
          className="h-7 w-7 p-0"
        >
          <Archive className="h-3 w-3" />
        </Button>
        {getStatusVariant(container.status) === 'running' ? (
          <Button
            size="sm"
            variant="ghost"
            onClick={(e) => {
              e.stopPropagation();
              onAction?.('stop', container.id);
            }}
            className="h-7 w-7 p-0"
          >
            <Square className="h-3 w-3" />
          </Button>
        ) : (
          <Button
            size="sm"
            variant="ghost"
            onClick={(e) => {
              e.stopPropagation();
              onAction?.('start', container.id);
            }}
            className="h-7 w-7 p-0"
          >
            <Play className="h-3 w-3" />
          </Button>
        )}
        <Button
          size="sm"
          variant="ghost"
          onClick={(e) => {
            e.stopPropagation();
            onAction?.('restart', container.id);
          }}
          className="h-7 w-7 p-0"
        >
          <RotateCcw className="h-3 w-3" />
        </Button>
      </div>
    </div>
  );
}

// Device Zone Component
function DeviceZone({ 
  device, 
  selectedContainers,
  onContainerSelect,
  onContainerAction,
  onContainerReorder 
}: {
  device: DeviceZone;
  selectedContainers: string[];
  onContainerSelect: (id: string, selected: boolean) => void;
  onContainerAction: (action: string, containerId: string) => void;
  onContainerReorder: (reorderedContainers: ContainerItem[]) => void;
}) {
  const { isDragging, draggedItem } = useDragDrop();
  const canAcceptContainer = draggedItem?.type === 'container' && draggedItem?.data?.deviceId !== device.id;

  return (
    <div className="space-y-4">
      {/* Device Header */}
      <div className="flex items-center justify-between p-4 glass rounded-lg border border-border/50">
        <div className="flex items-center gap-3">
          <Server className="h-5 w-5 text-primary" />
          <div>
            <h3 className="font-semibold">{device.hostname}</h3>
            <p className="text-sm text-muted-foreground">
              {device.containers.length} containers
            </p>
          </div>
        </div>
        <StatusBadge 
          status={device.status} 
          pulse={device.status === 'online'}
        >
          {device.status.charAt(0).toUpperCase() + device.status.slice(1)}
        </StatusBadge>
      </div>

      {/* Container Drop Zone */}
      <DropZone
        dropId={`device-${device.id}`}
        dropType="container"
        canDrop={(draggedItem) => draggedItem.data?.deviceId !== device.id}
        emptyMessage={device.containers.length === 0 ? "No containers - drop containers here to deploy" : "Drop containers here to move"}
        dragOverMessage="Deploy container to this device"
        className={cn(
          "min-h-32",
          device.containers.length > 0 && "hidden"
        )}
      />

      {/* Containers List */}
      {device.containers.length > 0 && (
        <div className="space-y-2">
          <SortableList
            items={device.containers}
            onReorder={onContainerReorder}
            renderItem={(container) => (
              <Draggable
                dragId={container.id}
                dragType="container"
                dragData={{ ...container, deviceId: device.id }}
                variant="card"
                className="hover:shadow-md"
              >
                <ContainerCard
                  container={container}
                  isSelected={selectedContainers.includes(container.id)}
                  onSelect={onContainerSelect}
                  onAction={onContainerAction}
                />
              </Draggable>
            )}
            itemKey={(container) => container.id}
            gap="sm"
          />

          {/* Additional Drop Zone for Non-Empty Devices */}
          <DropZone
            dropId={`device-${device.id}-add`}
            dropType="container"
            canDrop={(draggedItem) => draggedItem.data?.deviceId !== device.id}
            size="sm"
            emptyMessage="Drop containers here to move"
            className={cn(
              "border-dashed border-border/20",
              !canAcceptContainer && isDragging && "hidden"
            )}
          />
        </div>
      )}
    </div>
  );
}

// Main Container Management Component
export function DragDropContainers({
  containers,
  devices,
  selectedContainers,
  onContainerAction,
  onContainerMove,
  onContainerReorder,
  onSelectionChange,
  className
}: ContainerManagementProps) {
  const handleDrop = (draggedItem: any, targetId: string, targetType: string) => {
    if (draggedItem.type === 'container') {
      const deviceId = targetId.replace('device-', '').replace('-add', '');
      if (draggedItem.data.deviceId !== deviceId) {
        onContainerMove(draggedItem.data.id, deviceId);
      }
    }
  };

  const handleContainerSelect = (id: string, selected: boolean) => {
    const newSelection = selected
      ? [...selectedContainers, id]
      : selectedContainers.filter(cid => cid !== id);
    onSelectionChange(newSelection);
  };

  const handleBulkAction = (action: string) => {
    if (selectedContainers.length > 0) {
      onContainerAction(action, selectedContainers);
    }
  };

  const clearSelection = () => {
    onSelectionChange([]);
  };

  return (
    <DragDropProvider onDrop={handleDrop}>
      <div className={cn("space-y-6", className)}>
        {/* Unassigned Containers */}
        {containers.filter(c => !c.deviceId).length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Package className="h-5 w-5 text-muted-foreground" />
              <h2 className="text-lg font-semibold">Unassigned Containers</h2>
              <Badge variant="secondary" className="ml-2">
                {containers.filter(c => !c.deviceId).length}
              </Badge>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {containers
                .filter(container => !container.deviceId)
                .map(container => (
                  <Draggable
                    key={container.id}
                    dragId={container.id}
                    dragType="container"
                    dragData={container}
                    variant="card"
                    className="glass border border-border/50 hover:shadow-lg"
                  >
                    <ContainerCard
                      container={container}
                      isSelected={selectedContainers.includes(container.id)}
                      onSelect={handleContainerSelect}
                      onAction={onContainerAction}
                    />
                  </Draggable>
                ))}
            </div>
          </div>
        )}

        {/* Device Zones */}
        <div className="space-y-6">
          <div className="flex items-center gap-2">
            <Server className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold">Devices</h2>
            <Badge variant="secondary" className="ml-2">
              {devices.length}
            </Badge>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            {devices.map(device => (
              <DeviceZone
                key={device.id}
                device={device}
                selectedContainers={selectedContainers}
                onContainerSelect={handleContainerSelect}
                onContainerAction={onContainerAction}
                onContainerReorder={(reordered) => onContainerReorder(device.id, reordered)}
              />
            ))}
          </div>
        </div>

        {/* Bulk Actions Toolbar */}
        <BulkActions
          selectedItems={selectedContainers}
          onClearSelection={clearSelection}
        >
          <Button
            size="sm"
            variant="secondary"
            onClick={() => handleBulkAction('start')}
            className="gap-2"
          >
            <Play className="h-3 w-3" />
            Start All
          </Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => handleBulkAction('stop')}
            className="gap-2"
          >
            <Square className="h-3 w-3" />
            Stop All
          </Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => handleBulkAction('restart')}
            className="gap-2"
          >
            <RotateCcw className="h-3 w-3" />
            Restart All
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
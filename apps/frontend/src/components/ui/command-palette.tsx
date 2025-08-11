import * as React from "react"
import { Command as CommandPrimitive } from "cmdk"
import { Search, Server, Activity, Database, Box, Rocket } from "lucide-react"
import { cn, glassStyles, typography, animations, statusColors } from "@/lib/modern-design-system"
import { Dialog, DialogContent } from "@/components/ui/dialog"
import { useDevices } from "@/hooks/useDevices"

interface CommandPaletteProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

// Mock device data - will be replaced with real data from backend
const mockDevices = [
  { id: '1', hostname: 'web-server-01', ip: '192.168.1.10', status: 'online' as const, type: 'web' },
  { id: '2', hostname: 'app-server-01', ip: '192.168.1.11', status: 'online' as const, type: 'app' },
  { id: '3', hostname: 'db-server-01', ip: '192.168.1.12', status: 'warning' as const, type: 'database' },
  { id: '4', hostname: 'backup-server', ip: '192.168.1.15', status: 'online' as const, type: 'backup' },
  { id: '5', hostname: 'staging-01', ip: '192.168.1.20', status: 'offline' as const, type: 'staging' },
]

// Navigation shortcuts
const navigationItems = [
  { id: 'dashboard', label: 'Dashboard', href: '/', icon: Activity },
  { id: 'devices', label: 'Devices', href: '/devices', icon: Server },
  { id: 'containers', label: 'Containers', href: '/containers', icon: Box },
  { id: 'storage', label: 'Storage', href: '/storage', icon: Database },
  { id: 'deployments', label: 'Deployments', href: '/deployments', icon: Rocket },
]

const Command = React.forwardRef<
  React.ElementRef<typeof CommandPrimitive>,
  React.ComponentPropsWithoutRef<typeof CommandPrimitive>
>(({ className, ...props }, ref) => (
  <CommandPrimitive
    ref={ref}
    className={cn(
      "flex h-full w-full flex-col overflow-hidden",
      glassStyles.card,
      className
    )}
    {...props}
  />
))
Command.displayName = CommandPrimitive.displayName

const CommandInput = React.forwardRef<
  React.ElementRef<typeof CommandPrimitive.Input>,
  React.ComponentPropsWithoutRef<typeof CommandPrimitive.Input>
>(({ className, ...props }, ref) => (
  <div className="flex items-center gap-3 px-4 py-4 border-b border-white/10">
    <Search className="h-4 w-4 text-gray-400 flex-shrink-0" />
    <CommandPrimitive.Input
      ref={ref}
      className={cn(
        "flex-1 bg-transparent text-white placeholder:text-gray-400",
        "focus:outline-none focus:ring-0",
        typography.body.md,
        className
      )}
      placeholder="Search devices, navigate..."
      {...props}
    />
  </div>
))
CommandInput.displayName = CommandPrimitive.Input.displayName

const CommandList = React.forwardRef<
  React.ElementRef<typeof CommandPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof CommandPrimitive.List>
>(({ className, ...props }, ref) => (
  <CommandPrimitive.List
    ref={ref}
    className={cn(
      "max-h-[400px] overflow-y-auto overflow-x-hidden px-2 py-3",
      "scrollbar-thin scrollbar-track-transparent scrollbar-thumb-white/20",
      className
    )}
    {...props}
  />
))
CommandList.displayName = CommandPrimitive.List.displayName

const CommandEmpty = React.forwardRef<
  React.ElementRef<typeof CommandPrimitive.Empty>,
  React.ComponentPropsWithoutRef<typeof CommandPrimitive.Empty>
>(({ className, ...props }, ref) => (
  <CommandPrimitive.Empty
    ref={ref}
    className={cn(
      "py-8 text-center text-gray-400",
      typography.body.sm,
      className
    )}
    {...props}
  />
))
CommandEmpty.displayName = CommandPrimitive.Empty.displayName

const CommandGroup = React.forwardRef<
  React.ElementRef<typeof CommandPrimitive.Group>,
  React.ComponentPropsWithoutRef<typeof CommandPrimitive.Group>
>(({ className, ...props }, ref) => (
  <CommandPrimitive.Group
    ref={ref}
    className={cn(
      "overflow-hidden px-2 py-2",
      "[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-2",
      "[&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium",
      "[&_[cmdk-group-heading]]:text-gray-400 [&_[cmdk-group-heading]]:uppercase",
      "[&_[cmdk-group-heading]]:tracking-wider",
      className
    )}
    {...props}
  />
))
CommandGroup.displayName = CommandPrimitive.Group.displayName

const CommandItem = React.forwardRef<
  React.ElementRef<typeof CommandPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof CommandPrimitive.Item>
>(({ className, ...props }, ref) => (
  <CommandPrimitive.Item
    ref={ref}
    className={cn(
      "relative flex items-center gap-3 px-3 py-3 mx-1 rounded-xl",
      "text-gray-300 cursor-pointer select-none transition-all duration-200",
      "hover:bg-white/10 hover:text-white",
      "data-[selected=true]:bg-gradient-to-r data-[selected=true]:from-blue-600/20 data-[selected=true]:to-purple-600/20",
      "data-[selected=true]:text-white data-[selected=true]:border data-[selected=true]:border-blue-500/30",
      "data-[disabled=true]:pointer-events-none data-[disabled=true]:opacity-50",
      animations.fadeIn,
      className
    )}
    {...props}
  />
))
CommandItem.displayName = CommandPrimitive.Item.displayName

function getDeviceIcon(type: string) {
  switch (type) {
    case 'database':
      return Database
    case 'web':
    case 'app':
      return Server
    case 'backup':
    case 'staging':
      return Box
    default:
      return Server
  }
}

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const [selectedDevice, setSelectedDevice] = React.useState<string | null>(null)
  const { devices } = useDevices()

  const handleDeviceSelect = (deviceId: string) => {
    setSelectedDevice(deviceId)
    onOpenChange(false)
    // TODO: Implement device switching logic
    console.log('Selected device:', deviceId)
  }

  const handleNavigationSelect = (href: string) => {
    onOpenChange(false)
    window.location.href = href
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className={cn(
        "max-w-2xl p-0 border-0",
        glassStyles.elevated,
        animations.scaleIn
      )}>
        <Command className="border-0">
          <CommandInput />
          <CommandList>
            <CommandEmpty>No results found.</CommandEmpty>
            
            {/* Navigation Section */}
            <CommandGroup heading="Navigate">
              {navigationItems.map((item) => {
                const Icon = item.icon
                return (
                  <CommandItem
                    key={item.id}
                    value={item.label}
                    onSelect={() => handleNavigationSelect(item.href)}
                  >
                    <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-gray-700/50">
                      <Icon className="h-3 w-3" />
                    </div>
                    <span className={typography.body.sm}>{item.label}</span>
                  </CommandItem>
                )
              })}
            </CommandGroup>

            {/* Devices Section */}
            <CommandGroup heading="Devices">
              {devices.map((device) => {
                const DeviceIcon = getDeviceIcon(device.device_type)
                return (
                  <CommandItem
                    key={device.id}
                    value={`${device.hostname} ${device.ip_address || ''}`}
                    onSelect={() => handleDeviceSelect(device.id)}
                  >
                    <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-gray-700/50">
                      <DeviceIcon className="h-3 w-3" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className={cn(typography.body.sm, "font-mono font-semibold")}>
                        {device.hostname}
                      </div>
                      <div className={cn(typography.caption.sm, "text-gray-400")}>
                        {device.ip_address || 'No IP'} • {device.device_type}
                      </div>
                    </div>
                    <div className={cn(
                      "flex items-center gap-2",
                      selectedDevice === device.id && "opacity-100",
                      selectedDevice !== device.id && "opacity-60"
                    )}>
                      <div className={cn(
                        "w-2 h-2 rounded-full",
                        statusColors[device.status].indicator,
                        device.status === 'online' && "animate-pulse"
                      )} />
                      <span className={cn(
                        typography.caption.sm,
                        "capitalize",
                        statusColors[device.status].text
                      )}>
                        {device.status}
                      </span>
                    </div>
                  </CommandItem>
                )
              })}
              {devices.length === 0 && (
                <CommandItem disabled>
                  <div className="flex items-center gap-3 text-gray-500">
                    <Server className="h-4 w-4" />
                    <span className={typography.body.sm}>No devices found</span>
                  </div>
                </CommandItem>
              )}
            </CommandGroup>
          </CommandList>
        </Command>
      </DialogContent>
    </Dialog>
  )
}

// Hook for keyboard shortcut
export function useCommandPalette() {
  const [open, setOpen] = React.useState(false)

  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setOpen((open) => !open)
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [])

  return { open, setOpen }
}
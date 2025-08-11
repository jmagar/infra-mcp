import { useState } from 'react';
import { CommandPalette, useCommandPalette } from '@/components/ui/command-palette';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { useResponsiveSidebar } from '@/hooks/useResponsive';
import { ThemeToggle, SimpleThemeToggle } from '@/components/ui/theme-toggle';
import { NotificationCenter } from '@/components/notifications/NotificationCenter';
import { cn, typography, spacing, animations, glassStyles, statusColors } from '@/lib/modern-design-system';
import {
  Home,
  Server,
  Box,
  Database,
  Wifi,
  Rocket,
  BarChart3,
  Settings,
  Monitor,
  Menu,
  X,
  ChevronLeft,
  ChevronRight,
  Activity,
  Search,
  Command,
} from 'lucide-react';

// Enhanced navigation with descriptions and groupings
const navigation = [
  {
    name: 'Overview',
    items: [
      { 
        name: 'Dashboard', 
        href: '/', 
        icon: Home,
        description: 'System overview and metrics'
      },
      { 
        name: 'Monitoring', 
        href: '/monitoring', 
        icon: Activity,
        description: 'Real-time system monitoring'
      },
    ]
  },
  {
    name: 'Infrastructure',
    items: [
      { 
        name: 'Devices', 
        href: '/devices', 
        icon: Server,
        description: 'Manage infrastructure devices'
      },
      { 
        name: 'Containers', 
        href: '/containers', 
        icon: Box,
        description: 'Docker container management'
      },
      { 
        name: 'Storage', 
        href: '/storage', 
        icon: Database,
        description: 'ZFS and storage systems'
      },
      { 
        name: 'Networking', 
        href: '/networking', 
        icon: Wifi,
        description: 'Network and proxy configuration'
      },
    ]
  },
  {
    name: 'Operations',
    items: [
      { 
        name: 'Deployments', 
        href: '/deployments', 
        icon: Rocket,
        description: 'Deploy and manage services'
      },
      { 
        name: 'System', 
        href: '/system', 
        icon: Monitor,
        description: 'System administration'
      },
      { 
        name: 'Settings', 
        href: '/settings', 
        icon: Settings,
        description: 'Application configuration'
      },
    ]
  },
];

// Flatten navigation for mobile
const flatNavigation = navigation.flatMap(group => group.items);

export function AppLayout() {
  const { sidebarOpen, setSidebarOpen, shouldShowOverlay, isMobile } = useResponsiveSidebar();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const { open: commandPaletteOpen, setOpen: setCommandPaletteOpen } = useCommandPalette();
  const location = useLocation();

  const isActive = (href: string) => {
    return location.pathname === href || 
           (href !== '/' && location.pathname.startsWith(href + '/'));
  };

  return (
    <div className="h-screen flex bg-gradient-to-br from-slate-900 via-gray-900 to-zinc-900">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && isMobile && (
        <div 
          className="fixed inset-0 z-50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        >
          <div className="fixed inset-0 bg-black/60 backdrop-blur-md" />
          <div className="fixed inset-y-0 left-0 z-50 w-72 animate-slide-in-from-left">
            <MobileSidebar 
              navigation={flatNavigation}
              location={location}
              onClose={() => setSidebarOpen(false)}
              isActive={isActive}
            />
          </div>
        </div>
      )}

      {/* Desktop sidebar */}
      <aside className={cn(
        "hidden lg:flex lg:flex-col lg:fixed lg:inset-y-0 z-40 transition-all duration-500",
        glassStyles.elevated,
        "border-r border-white/10",
        sidebarCollapsed ? "lg:w-16" : "lg:w-72"
      )}>
        <DesktopSidebar
          navigation={navigation}
          location={location}
          collapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
          isActive={isActive}
        />
      </aside>

      {/* Main content */}
      <div className={cn(
        "flex flex-col flex-1 transition-all duration-300 ease-in-out",
        isMobile ? "lg:ml-0" : sidebarCollapsed ? "lg:ml-16" : "lg:ml-72"
      )}>
        {/* Modern Top header */}
        <header className={cn(
          "sticky top-0 z-30 flex h-16 items-center gap-4 px-6 transition-all duration-300",
          glassStyles.card,
          "border-b border-white/10"
        )}>
          <button
            type="button"
            className={cn(
              "lg:hidden p-2 -ml-2 rounded-lg transition-all duration-200",
              animations.hoverSubtle,
              "hover:bg-white/10"
            )}
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-5 w-5" />
            <span className="sr-only">Open sidebar</span>
          </button>

          <div className="flex flex-1 items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="relative">
                <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg blur opacity-75"></div>
                <div className="relative bg-gray-900 rounded-lg p-2">
                  <Activity className="h-6 w-6 text-blue-500" />
                </div>
              </div>
              <div>
                <h1 className={cn(typography.heading.lg, "bg-gradient-to-r from-white to-gray-300 bg-clip-text text-transparent")}>
                  {flatNavigation.find(item => isActive(item.href))?.name || 'Infrastructor'}
                </h1>
                <p className={cn(typography.caption.md, "text-gray-400")}>
                  Infrastructure Management Platform
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {/* Command Palette Trigger */}
              <button 
                onClick={() => setCommandPaletteOpen(true)}
                className={cn(
                  "flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all duration-200",
                  glassStyles.interactive,
                  "hover:bg-white/10"
                )}
              >
                <Search className="h-4 w-4" />
                <span className="hidden sm:inline text-gray-400">Search devices...</span>
                <div className="hidden sm:flex items-center gap-1 ml-2">
                  <kbd className="px-1.5 py-0.5 text-xs bg-gray-700 rounded border border-gray-600">⌘</kbd>
                  <kbd className="px-1.5 py-0.5 text-xs bg-gray-700 rounded border border-gray-600">K</kbd>
                </div>
              </button>
              <StatusIndicator />
              <NotificationCenter />
              <ThemeToggle variant="dropdown" size="sm" />
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-hidden">
          <div className="h-full overflow-y-auto scrollbar-thin">
            <div className={animations.fadeIn}>
              <Outlet />
            </div>
          </div>
        </main>
      </div>

      {/* Command Palette */}
      <CommandPalette 
        open={commandPaletteOpen} 
        onOpenChange={setCommandPaletteOpen} 
      />
    </div>
  );
}

// Modern status indicator component
function StatusIndicator() {
  return (
    <div className="flex items-center gap-2 text-sm text-gray-300 hover:text-white transition-colors">
      <div className={cn(
        "h-2 w-2 rounded-full transition-all duration-200",
        statusColors.online.indicator,
        animations.heartbeat
      )} />
      <span className="hidden sm:inline font-medium">Live Data</span>
    </div>
  );
}

// Mobile sidebar component
function MobileSidebar({ 
  navigation, 
  location, 
  onClose, 
  isActive 
}: {
  navigation: typeof flatNavigation;
  location: ReturnType<typeof useLocation>;
  onClose: () => void;
  isActive: (href: string) => boolean;
}) {
  return (
    <div className={cn("flex h-full flex-col", glassStyles.elevated, "border-r border-white/10")}>
      {/* Header */}
      <div className="flex h-16 items-center justify-between px-6 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg blur opacity-75"></div>
            <div className="relative h-8 w-8 rounded-lg bg-gray-900 flex items-center justify-center">
              <Server className="h-4 w-4 text-blue-500" />
            </div>
          </div>
          <h2 className={cn(typography.heading.md, "bg-gradient-to-r from-white to-gray-300 bg-clip-text text-transparent")}>
            Infrastructor
          </h2>
        </div>
        <button
          onClick={onClose}
          className={cn(
            "p-2 rounded-lg transition-all duration-200",
            animations.hoverSubtle,
            "hover:bg-white/10"
          )}
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-6 px-4 space-y-2 scrollbar-thin">
        {navigation.map((item) => (
          <Link
            key={item.href}
            to={item.href}
            onClick={onClose}
            className={cn(
              "flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-medium transition-all duration-200 group",
              animations.hoverCard,
              isActive(item.href)
                ? "bg-gradient-to-r from-blue-600/20 to-purple-600/20 text-white border border-blue-500/30"
                : "text-gray-300 hover:text-white hover:bg-white/5"
            )}
          >
            <div className={cn(
              "flex h-8 w-8 items-center justify-center rounded-lg transition-all duration-200",
              isActive(item.href) 
                ? "bg-blue-500/20 text-blue-400" 
                : "bg-gray-700/50 group-hover:bg-blue-500/10 group-hover:text-blue-400"
            )}>
              <item.icon className="h-4 w-4 flex-shrink-0" />
            </div>
            <div className="flex flex-col min-w-0 flex-1">
              <span className="truncate font-medium">{item.name}</span>
              <span className="text-xs opacity-70 truncate">{item.description}</span>
            </div>
          </Link>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-white/10 p-4">
        <div className="flex items-center justify-between">
          <span className={cn(typography.body.sm, "text-gray-400")}>Theme</span>
          <SimpleThemeToggle />
        </div>
      </div>
    </div>
  );
}

// Desktop sidebar component
function DesktopSidebar({ 
  navigation, 
  location, 
  collapsed, 
  onToggleCollapse, 
  isActive 
}: {
  navigation: typeof navigation;
  location: ReturnType<typeof useLocation>;
  collapsed: boolean;
  onToggleCollapse: () => void;
  isActive: (href: string) => boolean;
}) {
  return (
    <div className="flex h-full flex-col relative">
      {/* Header */}
      <div className="flex h-16 items-center justify-between px-4 border-b border-white/10">
        {!collapsed && (
          <div className={cn("flex items-center gap-3", animations.fadeIn)}>
            <div className="relative">
              <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg blur opacity-75"></div>
              <div className="relative h-8 w-8 rounded-lg bg-gray-900 flex items-center justify-center">
                <Server className="h-4 w-4 text-blue-500" />
              </div>
            </div>
            <h2 className={cn(typography.heading.md, "bg-gradient-to-r from-white to-gray-300 bg-clip-text text-transparent")}>
              Infrastructor
            </h2>
          </div>
        )}
        {collapsed && (
          <div className={cn("mx-auto", animations.fadeIn)}>
            <div className="relative">
              <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg blur opacity-75"></div>
              <div className="relative h-8 w-8 rounded-lg bg-gray-900 flex items-center justify-center">
                <Server className="h-4 w-4 text-blue-500" />
              </div>
            </div>
          </div>
        )}
        <button
          onClick={onToggleCollapse}
          className={cn(
            "p-2 rounded-lg transition-all duration-200 ml-auto",
            animations.hoverSubtle,
            "hover:bg-white/10"
          )}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <div className={cn("transition-transform duration-200", animations.iconBounce)}>
            {collapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </div>
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-6 px-4 space-y-6 scrollbar-thin">
        {navigation.map((group, groupIndex) => (
          <div key={group.name} className={animations.fadeIn} style={{ animationDelay: `${groupIndex * 100}ms` }}>
            {!collapsed && (
              <h3 className={cn(
                typography.caption.md,
                "px-3 mb-3 text-gray-400 uppercase tracking-wider font-semibold"
              )}>
                {group.name}
              </h3>
            )}
            {collapsed && (
              <div className="w-full h-px bg-gradient-to-r from-transparent via-white/10 to-transparent mb-4" />
            )}
            <div className="space-y-1">
              {group.items.map((item, itemIndex) => (
                <Link
                  key={item.href}
                  to={item.href}
                  className={cn(
                    "flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-medium transition-all duration-200 group relative",
                    animations.hoverCard,
                    collapsed ? "justify-center" : "",
                    isActive(item.href)
                      ? "bg-gradient-to-r from-blue-600/20 to-purple-600/20 text-white border border-blue-500/30"
                      : "text-gray-300 hover:text-white hover:bg-white/5"
                  )}
                  title={collapsed ? `${item.name} - ${item.description}` : undefined}
                  style={{ animationDelay: `${(groupIndex * 100) + (itemIndex * 50)}ms` }}
                >
                  <div className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-lg transition-all duration-200",
                    isActive(item.href) 
                      ? "bg-blue-500/20 text-blue-400" 
                      : "bg-gray-700/50 group-hover:bg-blue-500/10 group-hover:text-blue-400 group-hover:scale-110"
                  )}>
                    <item.icon className="h-4 w-4 flex-shrink-0" />
                  </div>
                  {!collapsed && (
                    <div className={cn("flex flex-col min-w-0 flex-1", animations.fadeIn)}>
                      <span className="truncate font-medium">{item.name}</span>
                      <span className="text-xs opacity-70 truncate leading-tight">
                        {item.description}
                      </span>
                    </div>
                  )}
                  {/* Active indicator */}
                  {isActive(item.href) && (
                    <div className={cn(
                      "absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 rounded-r-full",
                      "bg-gradient-to-b from-blue-500 to-purple-500",
                      animations.scaleIn
                    )} />
                  )}
                </Link>
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer */}
      {!collapsed && (
        <div className={cn(
          "border-t border-white/10 p-4", 
          glassStyles.subtle, 
          animations.fadeIn
        )}>
          <div className="flex items-center justify-between">
            <span className={cn(typography.body.sm, "text-gray-400")}>Theme</span>
            <ThemeToggle variant="dropdown" size="sm" />
          </div>
        </div>
      )}
      
      {/* Collapsed footer */}
      {collapsed && (
        <div className={cn(
          "border-t border-white/10 p-2 flex justify-center", 
          animations.fadeIn
        )}>
          <ThemeToggle variant="button" size="sm" />
        </div>
      )}
    </div>
  );
}
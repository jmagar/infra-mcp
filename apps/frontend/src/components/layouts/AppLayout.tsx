import { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { useResponsiveSidebar } from '@/hooks/useResponsive';
import { ThemeToggle, SimpleThemeToggle } from '@/components/ui/theme-toggle';
import { NotificationCenter } from '@/components/notifications/NotificationCenter';
import { cn, componentStyles } from '@/lib/design-system';
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
  const location = useLocation();

  const isActive = (href: string) => {
    return location.pathname === href || 
           (href !== '/' && location.pathname.startsWith(href + '/'));
  };

  return (
    <div className="h-screen flex bg-background">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && isMobile && (
        <div 
          className="fixed inset-0 z-50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        >
          <div className="fixed inset-0 bg-background/80 backdrop-blur-sm" />
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
        "hidden lg:flex lg:flex-col lg:fixed lg:inset-y-0 border-r border-border bg-card/30 backdrop-blur-xl transition-all duration-300 ease-in-out z-40",
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
        {/* Top header */}
        <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b border-border bg-background/80 backdrop-blur-xl px-6">
          <button
            type="button"
            className="lg:hidden p-2 -ml-2 rounded-lg hover:bg-muted transition-colors"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-5 w-5" />
            <span className="sr-only">Open sidebar</span>
          </button>

          <div className="flex flex-1 items-center justify-between">
            <div className="flex items-center gap-4">
              <h1 className={componentStyles.typography.heading.subsection}>
                {flatNavigation.find(item => isActive(item.href))?.name || 'Infrastructor'}
              </h1>
            </div>

            <div className="flex items-center gap-3">
              <StatusIndicator />
              <NotificationCenter />
              <ThemeToggle variant="dropdown" size="sm" />
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-hidden">
          <div className="h-full overflow-y-auto scrollbar-thin bg-gradient-subtle">
            <div className="animate-fade-in">
              <Outlet />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

// Status indicator component
function StatusIndicator() {
  return (
    <div className="flex items-center gap-2 text-sm text-muted-foreground">
      <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse" />
      <span className="hidden sm:inline">Online</span>
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
    <div className="flex h-full flex-col bg-card/95 backdrop-blur-xl border-r border-border">
      {/* Header */}
      <div className="flex h-16 items-center justify-between px-6 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg gradient-primary flex items-center justify-center">
            <Server className="h-4 w-4 text-primary-foreground" />
          </div>
          <h2 className={componentStyles.typography.heading.card}>
            Infrastructor
          </h2>
        </div>
        <button
          onClick={onClose}
          className="p-2 hover:bg-muted rounded-lg transition-colors"
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
              "flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-medium transition-all duration-200",
              isActive(item.href)
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground hover:bg-muted"
            )}
          >
            <item.icon className="h-5 w-5 flex-shrink-0" />
            <div className="flex flex-col min-w-0 flex-1">
              <span className="truncate">{item.name}</span>
              <span className="text-xs opacity-70 truncate">{item.description}</span>
            </div>
          </Link>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-border p-4">
        <div className="flex items-center justify-between">
          <span className={componentStyles.typography.body.small}>Theme</span>
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
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex h-16 items-center justify-between px-4 border-b border-border">
        {!collapsed && (
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-lg gradient-primary flex items-center justify-center">
              <Server className="h-4 w-4 text-primary-foreground" />
            </div>
            <h2 className={componentStyles.typography.heading.card}>
              Infrastructor
            </h2>
          </div>
        )}
        <button
          onClick={onToggleCollapse}
          className="p-2 hover:bg-muted rounded-lg transition-colors"
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-6 px-4 space-y-6 scrollbar-thin">
        {navigation.map((group) => (
          <div key={group.name}>
            {!collapsed && (
              <h3 className={cn(
                componentStyles.typography.label.small,
                "px-3 mb-3"
              )}>
                {group.name}
              </h3>
            )}
            <div className="space-y-1">
              {group.items.map((item) => (
                <Link
                  key={item.href}
                  to={item.href}
                  className={cn(
                    "flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-medium transition-all duration-200 group",
                    isActive(item.href)
                      ? "bg-primary text-primary-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted"
                  )}
                  title={collapsed ? `${item.name} - ${item.description}` : undefined}
                >
                  <item.icon className="h-5 w-5 flex-shrink-0" />
                  {!collapsed && (
                    <div className="flex flex-col min-w-0 flex-1">
                      <span className="truncate">{item.name}</span>
                      <span className="text-xs opacity-70 truncate">
                        {item.description}
                      </span>
                    </div>
                  )}
                </Link>
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer */}
      {!collapsed && (
        <div className="border-t border-border p-4">
          <div className="flex items-center justify-between">
            <span className={componentStyles.typography.body.small}>Theme</span>
            <ThemeToggle variant="dropdown" size="sm" />
          </div>
        </div>
      )}
    </div>
  );
}
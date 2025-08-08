import { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { useResponsiveSidebar } from '@/hooks/useResponsive';
import { navigation as navUtils, typography, spacing } from '@/lib/responsive';
import { ThemeToggle, SimpleThemeToggle } from '@/components/ui/theme-toggle';
import { NotificationCenter } from '@/components/notifications/NotificationCenter';
import {
  Home as HomeIcon,
  Server as ServerIcon,
  Box as CubeTransparentIcon,
  Database as CircleStackIcon,
  Wifi as WifiIcon,
  Rocket as RocketLaunchIcon,
  BarChart3 as ChartBarIcon,
  Settings as CogIcon,
  Monitor as ComputerDesktopIcon,
  Menu as Bars3Icon,
  X as XMarkIcon,
} from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'Devices', href: '/devices', icon: ServerIcon },
  { name: 'Containers', href: '/containers', icon: CubeTransparentIcon },
  { name: 'Storage', href: '/storage', icon: CircleStackIcon },
  { name: 'Networking', href: '/networking', icon: WifiIcon },
  { name: 'Deployments', href: '/deployments', icon: RocketLaunchIcon },
  { name: 'Monitoring', href: '/monitoring', icon: ChartBarIcon },
  { name: 'System', href: '/system', icon: ComputerDesktopIcon },
  { name: 'Settings', href: '/settings', icon: CogIcon },
];

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ');
}

export function AppLayout() {
  const { sidebarOpen, setSidebarOpen, shouldShowOverlay, isMobile } = useResponsiveSidebar();
  const location = useLocation();

  return (
    <div className="h-screen flex">
      {/* Mobile sidebar */}
      <div className={classNames(
        sidebarOpen ? navUtils.sidebar.mobile : 'hidden'
      )}>
        {shouldShowOverlay && (
          <div
            className={navUtils.sidebar.overlay}
            onClick={() => setSidebarOpen(false)}
          />
        )}
        <div className="relative flex-1 flex flex-col max-w-xs w-full pt-5 pb-4 bg-gray-800">
          <div className="absolute top-0 right-0 -mr-12 pt-2">
            <button
              type="button"
              className="ml-1 flex items-center justify-center h-10 w-10 rounded-full focus:outline-none focus:ring-2 focus:ring-inset focus:ring-white"
              onClick={() => setSidebarOpen(false)}
            >
              <XMarkIcon className="h-6 w-6 text-white" />
            </button>
          </div>
          <div className="flex-shrink-0 flex items-center px-4">
            <h1 className={`text-white ${typography.heading.section}`}>Infrastructor</h1>
          </div>
          <nav className="mt-5 flex-shrink-0 h-full divide-y divide-gray-700 overflow-y-auto">
            <div className={spacing.padding.section}>
              <div className="space-y-1">
                {navigation.map((item) => (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={classNames(
                      location.pathname === item.href || location.pathname.startsWith(item.href + '/')
                        ? 'bg-gray-900 text-white'
                        : 'text-gray-300 hover:text-white hover:bg-gray-700',
                      'group flex items-center px-3 py-2 text-sm leading-6 font-medium rounded-md transition-colors'
                    )}
                    onClick={() => setSidebarOpen(false)}
                  >
                    <item.icon className="mr-3 flex-shrink-0 h-5 w-5" />
                    {item.name}
                  </Link>
                ))}
              </div>
            </div>
            
            {/* Theme toggle at bottom of mobile sidebar */}
            <div className="px-4 py-3 border-t border-gray-700">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400">Theme</span>
                <SimpleThemeToggle />
              </div>
            </div>
          </nav>
        </div>
      </div>

      {/* Desktop sidebar */}
      <div className={navUtils.desktopMenu}>
        <div className="flex flex-col w-64">
          <div className="flex flex-col flex-grow pt-5 pb-4 overflow-y-auto bg-gray-800">
            <div className="flex items-center flex-shrink-0 px-4">
              <h1 className={`text-white ${typography.heading.section}`}>Infrastructor</h1>
            </div>
            <nav className="mt-5 flex-1 flex flex-col divide-y divide-gray-700 overflow-y-auto">
              <div className={spacing.padding.section}>
                <div className="space-y-1">
                  {navigation.map((item) => (
                    <Link
                      key={item.name}
                      to={item.href}
                      className={classNames(
                        location.pathname === item.href || location.pathname.startsWith(item.href + '/')
                          ? 'bg-gray-900 text-white'
                          : 'text-gray-300 hover:text-white hover:bg-gray-700',
                        'group flex items-center px-3 py-2 text-sm leading-6 font-medium rounded-md transition-colors'
                      )}
                    >
                      <item.icon className="mr-3 flex-shrink-0 h-5 w-5" />
                      {item.name}
                    </Link>
                  ))}
                </div>
              </div>
              
              {/* Theme toggle at bottom of desktop sidebar */}
              <div className="px-4 py-3 border-t border-gray-700 mt-auto">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-400">Theme</span>
                  <ThemeToggle variant="dropdown" size="sm" />
                </div>
              </div>
            </nav>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-col w-0 flex-1 overflow-hidden">
        {/* Mobile header */}
        <div className={`relative z-10 flex-shrink-0 flex h-16 bg-white dark:bg-gray-800 shadow ${navUtils.mobileMenu}`}>
          <button
            type="button"
            className="px-4 border-r border-gray-200 dark:border-gray-600 text-gray-500 dark:text-gray-400 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-500 transition-colors"
            onClick={() => setSidebarOpen(true)}
          >
            <Bars3Icon className="h-6 w-6" />
          </button>
          <div className="flex-1 px-4 flex justify-between items-center">
            <h1 className={`text-gray-900 dark:text-gray-100 ${typography.heading.card}`}>Infrastructor</h1>
            <div className="flex items-center space-x-3">
              {isMobile && (
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span className="text-xs text-gray-600 dark:text-gray-400">Online</span>
                </div>
              )}
              <NotificationCenter />
              <SimpleThemeToggle />
            </div>
          </div>
        </div>

        <main className="flex-1 relative overflow-y-auto focus:outline-none bg-gray-50 dark:bg-gray-900 transition-colors">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
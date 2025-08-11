import { useTheme } from '@/contexts/ThemeContext';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { 
  Sun as SunIcon, 
  Moon as MoonIcon, 
  Monitor as ComputerDesktopIcon,
  ChevronDown as ChevronDownIcon,
  Zap as AutoIcon,
  Clock as TimeIcon
} from 'lucide-react';

interface ThemeToggleProps {
  variant?: 'button' | 'dropdown';
  size?: 'sm' | 'default' | 'lg';
  showLabel?: boolean;
  className?: string;
}

export function ThemeToggle({ 
  variant = 'dropdown', 
  size = 'default',
  showLabel = false,
  className = '' 
}: ThemeToggleProps) {
  const { 
    theme, 
    resolvedTheme, 
    setTheme, 
    toggleTheme,
    isAmbientLightSupported,
    ambientLightLevel,
    timeBasedTheme,
    resetToSystem
  } = useTheme();

  const getThemeIcon = (themeName: string, resolved?: string) => {
    switch (themeName) {
      case 'light':
        return <SunIcon className="h-4 w-4" />;
      case 'dark':
        return <MoonIcon className="h-4 w-4" />;
      case 'system':
        return resolved === 'dark' ? 
          <MoonIcon className="h-4 w-4" /> : 
          <SunIcon className="h-4 w-4" />;
      case 'auto':
        return <AutoIcon className="h-4 w-4" />;
      default:
        return <ComputerDesktopIcon className="h-4 w-4" />;
    }
  };

  const getThemeLabel = (themeName: string) => {
    switch (themeName) {
      case 'light':
        return 'Light';
      case 'dark':
        return 'Dark';
      case 'system':
        return 'System';
      case 'auto':
        return 'Auto';
      default:
        return 'Theme';
    }
  };

  const getThemeDescription = (themeName: string) => {
    switch (themeName) {
      case 'light':
        return 'Always use light theme';
      case 'dark':
        return 'Always use dark theme';
      case 'system':
        return 'Follow system preference';
      case 'auto':
        return isAmbientLightSupported 
          ? `Smart theme (${ambientLightLevel ? Math.round(ambientLightLevel) : '?'} lux)`
          : `Time-based theme (${timeBasedTheme})`;
      default:
        return 'Select theme';
    }
  };

  if (variant === 'button') {
    return (
      <Button
        variant="ghost"
        size={size}
        onClick={toggleTheme}
        className={`${className} transition-all duration-200`}
        title={`Switch to ${theme === 'light' ? 'dark' : theme === 'dark' ? 'system' : 'light'} theme`}
      >
        {getThemeIcon(theme, resolvedTheme)}
        {showLabel && <span className="ml-2">{getThemeLabel(theme)}</span>}
      </Button>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size={size}
          className={`${className} transition-all duration-200`}
        >
          {getThemeIcon(theme, resolvedTheme)}
          {showLabel && (
            <>
              <span className="ml-2">{getThemeLabel(theme)}</span>
              <ChevronDownIcon className="ml-1 h-3 w-3" />
            </>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuItem
          onClick={() => setTheme('light')}
          className="cursor-pointer flex-col items-start py-3"
        >
          <div className="flex items-center w-full">
            <SunIcon className="mr-2 h-4 w-4" />
            <span className="font-medium">Light</span>
            {theme === 'light' && (
              <span className="ml-auto text-xs">✓</span>
            )}
          </div>
          <span className="text-xs text-muted-foreground mt-1 ml-6">
            Always use light theme
          </span>
        </DropdownMenuItem>
        
        <DropdownMenuItem
          onClick={() => setTheme('dark')}
          className="cursor-pointer flex-col items-start py-3"
        >
          <div className="flex items-center w-full">
            <MoonIcon className="mr-2 h-4 w-4" />
            <span className="font-medium">Dark</span>
            {theme === 'dark' && (
              <span className="ml-auto text-xs">✓</span>
            )}
          </div>
          <span className="text-xs text-muted-foreground mt-1 ml-6">
            Always use dark theme
          </span>
        </DropdownMenuItem>
        
        <DropdownMenuItem
          onClick={() => setTheme('system')}
          className="cursor-pointer flex-col items-start py-3"
        >
          <div className="flex items-center w-full">
            <ComputerDesktopIcon className="mr-2 h-4 w-4" />
            <span className="font-medium">System</span>
            {theme === 'system' && (
              <span className="ml-auto text-xs">✓</span>
            )}
          </div>
          <span className="text-xs text-muted-foreground mt-1 ml-6">
            Follow system preference
          </span>
        </DropdownMenuItem>
        
        <DropdownMenuItem
          onClick={() => setTheme('auto')}
          className="cursor-pointer flex-col items-start py-3"
        >
          <div className="flex items-center w-full">
            <AutoIcon className="mr-2 h-4 w-4" />
            <span className="font-medium">Auto</span>
            {theme === 'auto' && (
              <span className="ml-auto text-xs">✓</span>
            )}
          </div>
          <span className="text-xs text-muted-foreground mt-1 ml-6">
            {getThemeDescription('auto')}
          </span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

// Simplified toggle for mobile/compact layouts
export function SimpleThemeToggle({ className = '' }: { className?: string }) {
  const { toggleTheme, resolvedTheme } = useTheme();
  
  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={toggleTheme}
      className={`${className} p-2 transition-all duration-200`}
      title={`Switch to ${resolvedTheme === 'light' ? 'dark' : 'light'} mode`}
    >
      {resolvedTheme === 'light' ? (
        <MoonIcon className="h-4 w-4" />
      ) : (
        <SunIcon className="h-4 w-4" />
      )}
    </Button>
  );
}
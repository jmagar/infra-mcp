import { createContext, useContext, useEffect, useState } from 'react';
import { useAdvancedTheme, type ThemeMode, type ActualTheme } from '../hooks/useAdvancedTheme';

type Theme = ThemeMode; // Extend to support 'auto' mode
type ResolvedTheme = ActualTheme;

interface ThemeContextType {
  theme: Theme;
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  // Advanced theme features
  isAmbientLightSupported: boolean;
  ambientLightLevel: number | null;
  isReducedMotion: boolean;
  isHighContrast: boolean;
  timeBasedTheme: ActualTheme;
  resetToSystem: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

interface ThemeProviderProps {
  children: React.ReactNode;
  defaultTheme?: Theme;
  storageKey?: string;
}

export function ThemeProvider({
  children,
  defaultTheme = 'system',
  storageKey = 'infrastructor-theme',
}: ThemeProviderProps) {
  const advancedTheme = useAdvancedTheme();

  // Initialize from localStorage if available
  useEffect(() => {
    if (typeof window === 'undefined') return;
    
    try {
      const stored = localStorage.getItem(storageKey) as Theme;
      if (stored && stored !== advancedTheme.mode) {
        advancedTheme.setMode(stored);
      }
    } catch {
      // Ignore localStorage errors
    }
  }, [storageKey, advancedTheme]);

  // Persist theme changes to localStorage
  useEffect(() => {
    if (typeof window === 'undefined') return;
    
    try {
      localStorage.setItem(storageKey, advancedTheme.mode);
    } catch {
      // Ignore localStorage errors
    }
  }, [advancedTheme.mode, storageKey]);

  return (
    <ThemeContext.Provider
      value={{
        theme: advancedTheme.mode,
        resolvedTheme: advancedTheme.actualTheme,
        setTheme: advancedTheme.setMode,
        toggleTheme: advancedTheme.toggleTheme,
        isAmbientLightSupported: advancedTheme.isAmbientLightSupported,
        ambientLightLevel: advancedTheme.ambientLightLevel,
        isReducedMotion: advancedTheme.isReducedMotion,
        isHighContrast: advancedTheme.isHighContrast,
        timeBasedTheme: advancedTheme.timeBasedTheme,
        resetToSystem: advancedTheme.resetToSystem,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

// Theme configuration constants
export const themeConfig = {
  colors: {
    light: {
      background: 'bg-white',
      surface: 'bg-gray-50',
      card: 'bg-white',
      border: 'border-gray-200',
      text: {
        primary: 'text-gray-900',
        secondary: 'text-gray-600',
        muted: 'text-gray-500',
      },
      accent: {
        primary: 'bg-blue-600 text-white',
        secondary: 'bg-gray-100 text-gray-900',
      },
    },
    dark: {
      background: 'dark:bg-gray-900',
      surface: 'dark:bg-gray-800',
      card: 'dark:bg-gray-800',
      border: 'dark:border-gray-700',
      text: {
        primary: 'dark:text-gray-100',
        secondary: 'dark:text-gray-300',
        muted: 'dark:text-gray-400',
      },
      accent: {
        primary: 'dark:bg-blue-500 dark:text-white',
        secondary: 'dark:bg-gray-700 dark:text-gray-100',
      },
    },
  },
  transitions: 'transition-colors duration-200',
} as const;

// Utility function to combine theme classes
export function themeClasses(lightClass: string, darkClass?: string): string {
  if (!darkClass) {
    return `${lightClass} ${themeConfig.transitions}`;
  }
  return `${lightClass} ${darkClass} ${themeConfig.transitions}`;
}
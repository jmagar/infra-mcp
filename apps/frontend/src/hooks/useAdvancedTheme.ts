import { useEffect, useState, useCallback } from 'react';

export type ThemeMode = 'light' | 'dark' | 'system' | 'auto';
export type ActualTheme = 'light' | 'dark';

interface AdvancedThemeState {
  mode: ThemeMode;
  actualTheme: ActualTheme;
  isAmbientLightSupported: boolean;
  ambientLightLevel: number | null;
  isReducedMotion: boolean;
  isHighContrast: boolean;
  timeBasedTheme: ActualTheme;
}

interface AdvancedThemeActions {
  setMode: (mode: ThemeMode) => void;
  toggleTheme: () => void;
  applyTheme: (theme: ActualTheme) => void;
  resetToSystem: () => void;
}

/**
 * Advanced theme hook with ambient light adaptation, time-based switching,
 * and accessibility preferences detection
 */
export function useAdvancedTheme(): AdvancedThemeState & AdvancedThemeActions {
  const [mode, setModeState] = useState<ThemeMode>(() => {
    if (typeof window === 'undefined') return 'system';
    return (localStorage.getItem('theme-mode') as ThemeMode) || 'system';
  });

  const [actualTheme, setActualTheme] = useState<ActualTheme>('light');
  const [isAmbientLightSupported, setIsAmbientLightSupported] = useState(false);
  const [ambientLightLevel, setAmbientLightLevel] = useState<number | null>(null);
  const [isReducedMotion, setIsReducedMotion] = useState(false);
  const [isHighContrast, setIsHighContrast] = useState(false);
  const [timeBasedTheme, setTimeBasedTheme] = useState<ActualTheme>('light');

  // Get system theme preference
  const getSystemTheme = useCallback((): ActualTheme => {
    if (typeof window === 'undefined') return 'light';
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }, []);

  // Get time-based theme (dark at night, light during day)
  const getTimeBasedTheme = useCallback((): ActualTheme => {
    const hour = new Date().getHours();
    // Dark mode from 8 PM to 7 AM
    return (hour >= 20 || hour < 7) ? 'dark' : 'light';
  }, []);

  // Get ambient light based theme
  const getAmbientLightTheme = useCallback((lightLevel: number): ActualTheme => {
    // If ambient light is very low (< 10 lux), use dark theme
    // If moderate light (10-50 lux), use system preference
    // If bright light (> 50 lux), use light theme
    if (lightLevel < 10) return 'dark';
    if (lightLevel > 50) return 'light';
    return getSystemTheme();
  }, [getSystemTheme]);

  // Apply theme to document
  const applyTheme = useCallback((theme: ActualTheme) => {
    if (typeof window === 'undefined') return;
    
    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(theme);
    
    // Apply additional theme-related classes
    if (isHighContrast) {
      root.classList.add('high-contrast');
    } else {
      root.classList.remove('high-contrast');
    }
    
    if (isReducedMotion) {
      root.classList.add('reduce-motion');
    } else {
      root.classList.remove('reduce-motion');
    }
    
    // Update meta theme color
    const metaThemeColor = document.querySelector('meta[name="theme-color"]');
    if (metaThemeColor) {
      metaThemeColor.setAttribute('content', theme === 'dark' ? '#0f172a' : '#ffffff');
    }
    
    setActualTheme(theme);
  }, [isHighContrast, isReducedMotion]);

  // Determine actual theme based on mode
  const determineActualTheme = useCallback((): ActualTheme => {
    switch (mode) {
      case 'light':
        return 'light';
      case 'dark':
        return 'dark';
      case 'system':
        return getSystemTheme();
      case 'auto':
        // Auto mode uses ambient light if available, otherwise time-based
        if (isAmbientLightSupported && ambientLightLevel !== null) {
          return getAmbientLightTheme(ambientLightLevel);
        }
        return timeBasedTheme;
      default:
        return getSystemTheme();
    }
  }, [mode, getSystemTheme, isAmbientLightSupported, ambientLightLevel, getAmbientLightTheme, timeBasedTheme]);

  // Initialize ambient light sensor
  useEffect(() => {
    if (typeof window === 'undefined' || !('AmbientLightSensor' in window)) {
      setIsAmbientLightSupported(false);
      return;
    }

    try {
      // @ts-ignore - AmbientLightSensor is experimental
      const sensor = new AmbientLightSensor({ frequency: 1 });
      
      sensor.addEventListener('reading', () => {
        // @ts-ignore
        setAmbientLightLevel(sensor.illuminance);
      });
      
      sensor.addEventListener('error', () => {
        setIsAmbientLightSupported(false);
      });
      
      sensor.start();
      setIsAmbientLightSupported(true);
      
      return () => {
        sensor.stop();
      };
    } catch (error) {
      setIsAmbientLightSupported(false);
    }
  }, []);

  // Monitor system theme changes
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = () => {
      if (mode === 'system') {
        applyTheme(getSystemTheme());
      }
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [mode, getSystemTheme, applyTheme]);

  // Monitor accessibility preferences
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const contrastQuery = window.matchMedia('(prefers-contrast: high)');

    const updateMotionPreference = () => setIsReducedMotion(motionQuery.matches);
    const updateContrastPreference = () => setIsHighContrast(contrastQuery.matches);

    updateMotionPreference();
    updateContrastPreference();

    motionQuery.addEventListener('change', updateMotionPreference);
    contrastQuery.addEventListener('change', updateContrastPreference);

    return () => {
      motionQuery.removeEventListener('change', updateMotionPreference);
      contrastQuery.removeEventListener('change', updateContrastPreference);
    };
  }, []);

  // Update time-based theme every minute
  useEffect(() => {
    const updateTimeBasedTheme = () => {
      setTimeBasedTheme(getTimeBasedTheme());
    };

    updateTimeBasedTheme();
    const interval = setInterval(updateTimeBasedTheme, 60000); // Update every minute

    return () => clearInterval(interval);
  }, [getTimeBasedTheme]);

  // Apply theme when any dependency changes
  useEffect(() => {
    const newTheme = determineActualTheme();
    applyTheme(newTheme);
  }, [determineActualTheme, applyTheme]);

  // Persist theme mode to localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('theme-mode', mode);
    }
  }, [mode]);

  const setMode = useCallback((newMode: ThemeMode) => {
    setModeState(newMode);
  }, []);

  const toggleTheme = useCallback(() => {
    if (mode === 'light') {
      setMode('dark');
    } else if (mode === 'dark') {
      setMode('light');
    } else {
      // If in system or auto mode, toggle based on current actual theme
      setMode(actualTheme === 'light' ? 'dark' : 'light');
    }
  }, [mode, actualTheme, setMode]);

  const resetToSystem = useCallback(() => {
    setMode('system');
  }, [setMode]);

  return {
    mode,
    actualTheme,
    isAmbientLightSupported,
    ambientLightLevel,
    isReducedMotion,
    isHighContrast,
    timeBasedTheme,
    setMode,
    toggleTheme,
    applyTheme,
    resetToSystem,
  };
}
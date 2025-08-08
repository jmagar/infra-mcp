import { useState, useEffect } from 'react';
import { breakpoints } from '@/lib/responsive';

// Convert breakpoint strings to numbers
const breakpointValues = {
  sm: parseInt(breakpoints.sm),
  md: parseInt(breakpoints.md), 
  lg: parseInt(breakpoints.lg),
  xl: parseInt(breakpoints.xl),
  '2xl': parseInt(breakpoints['2xl']),
} as const;

type Breakpoint = keyof typeof breakpointValues;

interface ResponsiveState {
  width: number;
  height: number;
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
  isLarge: boolean;
  breakpoint: Breakpoint;
}

export function useResponsive(): ResponsiveState {
  const [state, setState] = useState<ResponsiveState>(() => {
    // Safe default values for SSR
    if (typeof window === 'undefined') {
      return {
        width: 1024,
        height: 768,
        isMobile: false,
        isTablet: false,
        isDesktop: true,
        isLarge: false,
        breakpoint: 'lg',
      };
    }

    const width = window.innerWidth;
    const height = window.innerHeight;

    return {
      width,
      height,
      isMobile: width < breakpointValues.md,
      isTablet: width >= breakpointValues.md && width < breakpointValues.lg,
      isDesktop: width >= breakpointValues.lg && width < breakpointValues.xl,
      isLarge: width >= breakpointValues.xl,
      breakpoint: getBreakpoint(width),
    };
  });

  useEffect(() => {
    function handleResize() {
      const width = window.innerWidth;
      const height = window.innerHeight;

      setState({
        width,
        height,
        isMobile: width < breakpointValues.md,
        isTablet: width >= breakpointValues.md && width < breakpointValues.lg,
        isDesktop: width >= breakpointValues.lg && width < breakpointValues.xl,
        isLarge: width >= breakpointValues.xl,
        breakpoint: getBreakpoint(width),
      });
    }

    window.addEventListener('resize', handleResize);
    
    // Call immediately to set initial state
    handleResize();
    
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return state;
}

function getBreakpoint(width: number): Breakpoint {
  if (width >= breakpointValues['2xl']) return '2xl';
  if (width >= breakpointValues.xl) return 'xl';
  if (width >= breakpointValues.lg) return 'lg';
  if (width >= breakpointValues.md) return 'md';
  return 'sm';
}

// Hook for checking specific breakpoints
export function useBreakpoint(breakpoint: Breakpoint): boolean {
  const { width } = useResponsive();
  return width >= breakpointValues[breakpoint];
}

// Hook for getting responsive grid columns
export function useResponsiveGrid(config: {
  mobile?: number;
  tablet?: number;
  desktop?: number;
  large?: number;
}): number {
  const { isMobile, isTablet, isDesktop, isLarge } = useResponsive();
  
  if (isLarge && config.large) return config.large;
  if (isDesktop && config.desktop) return config.desktop;
  if (isTablet && config.tablet) return config.tablet;
  return config.mobile || 1;
}

// Hook for responsive table columns
export function useResponsiveTable<T>(
  columns: Array<T & { hideOnMobile?: boolean; hideOnTablet?: boolean; hideOnDesktop?: boolean }>
): Array<T> {
  const { isMobile, isTablet, isDesktop } = useResponsive();
  
  return columns.filter(column => {
    if (isMobile && column.hideOnMobile) return false;
    if (isTablet && column.hideOnTablet) return false;
    if (isDesktop && column.hideOnDesktop) return false;
    return true;
  });
}

// Hook for responsive sidebar state
export function useResponsiveSidebar() {
  const { isMobile } = useResponsive();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  
  // Close sidebar when switching to desktop
  useEffect(() => {
    if (!isMobile) {
      setSidebarOpen(false);
    }
  }, [isMobile]);

  return {
    sidebarOpen,
    setSidebarOpen,
    isMobile,
    shouldShowOverlay: isMobile && sidebarOpen,
  };
}
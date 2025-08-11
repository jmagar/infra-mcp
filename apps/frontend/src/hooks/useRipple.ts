import { useCallback, useRef } from 'react';

interface RippleOptions {
  color?: string;
  duration?: number;
  disabled?: boolean;
}

export function useRipple(options: RippleOptions = {}) {
  const {
    color = 'currentColor',
    duration = 600,
    disabled = false,
  } = options;

  const rippleRef = useRef<HTMLElement | null>(null);

  const createRipple = useCallback((event: React.MouseEvent<HTMLElement>) => {
    if (disabled || !rippleRef.current) return;

    const button = rippleRef.current;
    const rect = button.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = event.clientX - rect.left - size / 2;
    const y = event.clientY - rect.top - size / 2;

    // Remove existing ripples
    const existingRipples = button.querySelectorAll('[data-ripple]');
    existingRipples.forEach(ripple => ripple.remove());

    // Create ripple element
    const ripple = document.createElement('span');
    ripple.setAttribute('data-ripple', 'true');
    ripple.style.cssText = `
      position: absolute;
      top: ${y}px;
      left: ${x}px;
      width: ${size}px;
      height: ${size}px;
      background-color: ${color};
      border-radius: 50%;
      opacity: 0.3;
      pointer-events: none;
      transform: scale(0);
      animation: ripple-expand ${duration}ms ease-out;
      z-index: 0;
    `;

    button.appendChild(ripple);

    // Clean up ripple after animation
    setTimeout(() => {
      if (ripple.parentNode) {
        ripple.parentNode.removeChild(ripple);
      }
    }, duration);
  }, [color, duration, disabled]);

  const addRippleStyles = useCallback((element: HTMLElement | null) => {
    if (!element) return;

    // Ensure the button has relative positioning and overflow hidden for ripple effect
    element.style.position = element.style.position || 'relative';
    element.style.overflow = 'hidden';

    // Add the ripple keyframes if not already added
    if (!document.querySelector('[data-ripple-styles]')) {
      const style = document.createElement('style');
      style.setAttribute('data-ripple-styles', 'true');
      style.textContent = `
        @keyframes ripple-expand {
          0% { transform: scale(0); opacity: 0.3; }
          50% { opacity: 0.1; }
          100% { transform: scale(1); opacity: 0; }
        }
      `;
      document.head.appendChild(style);
    }
  }, []);

  const setRippleRef = useCallback((element: HTMLElement | null) => {
    rippleRef.current = element;
    addRippleStyles(element);
  }, [addRippleStyles]);

  return {
    ref: setRippleRef,
    onMouseDown: createRipple,
  };
}

// Enhanced button hook with multiple interaction features
export function useButtonInteractions(options: RippleOptions & {
  hapticFeedback?: boolean;
  soundFeedback?: boolean;
} = {}) {
  const { hapticFeedback = false, soundFeedback = false, ...rippleOptions } = options;
  const ripple = useRipple(rippleOptions);

  const handleInteraction = useCallback((event: React.MouseEvent<HTMLElement>) => {
    // Haptic feedback (if supported)
    if (hapticFeedback && 'vibrate' in navigator) {
      navigator.vibrate(10);
    }

    // Sound feedback (optional - could be implemented with Web Audio API)
    if (soundFeedback) {
      // Could play a subtle click sound here
      console.debug('Sound feedback triggered');
    }

    // Trigger ripple effect
    ripple.onMouseDown(event);
  }, [hapticFeedback, soundFeedback, ripple]);

  return {
    ref: ripple.ref,
    onMouseDown: handleInteraction,
  };
}
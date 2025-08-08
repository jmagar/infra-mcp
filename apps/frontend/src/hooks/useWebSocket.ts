/**
 * WebSocket Hook
 * React hook for WebSocket connection management and real-time data streaming
 */

import { useEffect, useRef, useState, useCallback } from 'react';

export interface WebSocketMessage {
  type: string;
  data: unknown;
  timestamp: string;
}

export interface UseWebSocketOptions {
  url?: string;
  reconnect?: boolean;
  reconnectInterval?: number;
  reconnectAttempts?: number;
  onOpen?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (event: Event) => void;
  onMessage?: (message: WebSocketMessage) => void;
  autoConnect?: boolean;
}

export interface WebSocketState {
  isConnected: boolean;
  isConnecting: boolean;
  lastMessage: WebSocketMessage | null;
  error: Error | null;
  reconnectCount: number;
}

function resolveWsBase(): string {
  // If explicit WS base provided, use it
  const explicit = import.meta.env.VITE_WS_BASE_URL as string | undefined;
  if (explicit && explicit.trim().length > 0) return explicit;

  // Try to derive from API base if absolute
  const apiBase = (import.meta.env.VITE_API_BASE_URL as string | undefined) || '';
  if (apiBase.startsWith('http://') || apiBase.startsWith('https://')) {
    try {
      const u = new URL(apiBase);
      const wsScheme = u.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${wsScheme}//${u.host}`;
    } catch {
      // fall through
    }
  }

  // Fallback: use current host with configured API port or default 9101
  const port = (import.meta.env.VITE_API_PORT as string | undefined) || '9101';
  const isSecure = window.location.protocol === 'https:';
  const scheme = isSecure ? 'wss:' : 'ws:';
  const host = window.location.hostname;
  return `${scheme}//${host}:${port}`;
}

const WS_BASE_URL = resolveWsBase();

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    url = `${WS_BASE_URL}/ws/stream`,
    reconnect = true,
    reconnectInterval = 5000,
    reconnectAttempts = 5,
    onOpen,
    onClose,
    onError,
    onMessage,
    autoConnect = true,
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectCountRef = useRef(0);

  const [state, setState] = useState<WebSocketState>({
    isConnected: false,
    isConnecting: false,
    lastMessage: null,
    error: null,
    reconnectCount: 0,
  });

  // Get auth token for WebSocket authentication
  const getAuthToken = useCallback(() => {
    return localStorage.getItem('auth_token');
  }, []);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setState(prev => ({ ...prev, isConnecting: true, error: null }));

    try {
      // Add auth token to URL if available
      const token = getAuthToken();
      const wsUrl = token ? `${url}?token=${token}` : url;
      
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = (event) => {
        console.log('[WebSocket] Connected');
        setState(prev => ({
          ...prev,
          isConnected: true,
          isConnecting: false,
          error: null,
        }));
        reconnectCountRef.current = 0;
        onOpen?.(event);
      };

      ws.onclose = (event) => {
        console.log('[WebSocket] Disconnected:', event.code, event.reason);
        setState(prev => ({
          ...prev,
          isConnected: false,
          isConnecting: false,
        }));
        onClose?.(event);

        // Attempt reconnection if enabled
        if (reconnect && reconnectCountRef.current < reconnectAttempts) {
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectCountRef.current++;
            setState(prev => ({ ...prev, reconnectCount: reconnectCountRef.current }));
            console.log(`[WebSocket] Reconnecting... (${reconnectCountRef.current}/${reconnectAttempts})`);
            connect();
          }, reconnectInterval);
        }
      };

      ws.onerror = (event) => {
        console.error('[WebSocket] Error:', event);
        const error = new Error('WebSocket connection error');
        setState(prev => ({
          ...prev,
          error,
          isConnecting: false,
        }));
        onError?.(event);
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setState(prev => ({ ...prev, lastMessage: message }));
          onMessage?.(message);
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error);
        }
      };
    } catch (error) {
      console.error('[WebSocket] Failed to create connection:', error);
      setState(prev => ({
        ...prev,
        error: error as Error,
        isConnecting: false,
      }));
    }
  }, [url, getAuthToken, reconnect, reconnectInterval, reconnectAttempts, onOpen, onClose, onError, onMessage]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setState(prev => ({
      ...prev,
      isConnected: false,
      isConnecting: false,
    }));
  }, []);

  // Send message through WebSocket
  const sendMessage = useCallback((message: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const data = typeof message === 'string' ? message : JSON.stringify(message);
      wsRef.current.send(data);
      return true;
    }
    console.warn('[WebSocket] Cannot send message - not connected');
    return false;
  }, []);

  // Subscribe to specific event types
  const subscribe = useCallback((eventType: string, data?: unknown) => {
    return sendMessage({
      type: 'subscribe',
      event: eventType,
      data,
      timestamp: new Date().toISOString(),
    });
  }, [sendMessage]);

  // Unsubscribe from specific event types
  const unsubscribe = useCallback((eventType: string) => {
    return sendMessage({
      type: 'unsubscribe',
      event: eventType,
      timestamp: new Date().toISOString(),
    });
  }, [sendMessage]);

  // Auto-connect on mount if enabled
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]); // Only run on mount/unmount

  return {
    // State
    ...state,
    
    // Methods
    connect,
    disconnect,
    sendMessage,
    subscribe,
    unsubscribe,
  };
}

// Specialized hook for metrics streaming
export function useMetricsStream(deviceIds?: string[]) {
  const handleMessage = useCallback((message: WebSocketMessage) => {
    if (message.type === 'metrics') {
      // Handle metrics data
      console.log('[Metrics]', message.data);
    }
  }, []);

  const ws = useWebSocket({
    onMessage: handleMessage,
  });

  useEffect(() => {
    if (ws.isConnected && deviceIds?.length) {
      ws.subscribe('metrics', { device_ids: deviceIds });
    }
  }, [ws, ws.isConnected, ws.subscribe, deviceIds]);

  return ws;
}

// Specialized hook for container status streaming
export function useContainerStream(deviceId?: string) {
  const [containers, setContainers] = useState<unknown[]>([]);

  const handleMessage = useCallback((message: WebSocketMessage) => {
    if (message.type === 'container_update') {
      const data = message.data as { containers?: unknown[] } | null;
      const next = (data && Array.isArray(data.containers)) ? data.containers : [];
      setContainers(next);
    }
  }, []);

  const ws = useWebSocket({
    onMessage: handleMessage,
  });

  useEffect(() => {
    if (ws.isConnected && deviceId) {
      ws.subscribe('containers', { device_id: deviceId });
    }
  }, [ws, ws.isConnected, ws.subscribe, deviceId]);

  return {
    ...ws,
    containers,
  };
}

// Specialized hook for system alerts
export function useAlertsStream() {
  const [alerts, setAlerts] = useState<unknown[]>([]);

  const handleMessage = useCallback((message: WebSocketMessage) => {
    if (message.type === 'alert') {
      setAlerts(prev => [message.data, ...prev].slice(0, 100)); // Keep last 100 alerts
    }
  }, []);

  const ws = useWebSocket({
    onMessage: handleMessage,
  });

  useEffect(() => {
    if (ws.isConnected) {
      ws.subscribe('alerts');
    }
  }, [ws, ws.isConnected, ws.subscribe]);

  return {
    ...ws,
    alerts,
    clearAlerts: () => setAlerts([]),
  };
}
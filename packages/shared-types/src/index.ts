/**
 * @infrastructor/shared-types
 * 
 * Shared TypeScript type definitions for the Infrastructor project.
 * These types are used by both the frontend and backend to ensure
 * type safety and consistency across the application.
 */

// Export all common types
export * from './common';

// Export device-related types
export * from './device';

// Export system metrics types
export * from './system-metrics';

// Export ZFS types
export * from './zfs';

// Export container types
export * from './container';

// Export proxy configuration types
export * from './proxy-config';

// Export user and authentication types
export * from './user';

// Export drive health types
export * from './drive-health';

// Export logs types
export * from './logs';

// Export network types
export * from './network';

// Export compose deployment types
export * from './compose-deployment';

// Export backup types
export * from './backup';

// Export VM types
export * from './vm';

// Export updates types
export * from './updates';

// Re-export commonly used types at the top level for convenience
export type {
  APIResponse,
  PaginatedResponse,
  ErrorResponse,
  HealthCheckResponse,
  DeviceStatus,
  HealthStatus,
  LogLevel,
} from './common';

export type {
  DeviceResponse,
  DeviceList,
  DeviceHealth,
} from './device';

export type {
  SystemMetricResponse,
  SystemMetricsList,
  SystemMetricsSummary,
} from './system-metrics';

export type {
  ContainerResponse,
  ContainerList,
  ContainerStatus,
  ContainerStats,
} from './container';

export type {
  ZFSPoolResponse,
  ZFSDatasetResponse,
  ZFSSnapshotResponse,
  ZFSHealthCheck,
} from './zfs';

export type {
  ProxyConfigResponse,
  ProxyConfigList,
  ProxyConfigStatus,
} from './proxy-config';

export type {
  UserResponse,
  UserRole,
  LoginResponse,
  UserSession,
} from './user';

// Version export for package tracking
export const VERSION = '1.0.0';
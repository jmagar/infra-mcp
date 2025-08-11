/**
 * Services Index
 * Centralized export of all API services
 */

// Export API utilities and clients
export { 
  api, 
  apiClient, 
  apiRequest, 
  checkAPIHealth, 
  healthRequest,
  deviceApi,
  containerApi,
  composeApi,
  proxyApi,
  zfsApi,
  vmApi,
  systemApi,
} from './api';

// Export service objects
export { containerService } from './containers';
export { systemMetricsService } from './system-metrics';
export { deviceService } from './devices';
export { vmService } from './vms';
export { zfsService } from './zfs';

// Export WebSocket client
export * from './ws';
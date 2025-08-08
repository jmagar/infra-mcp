/**
 * API Integration Test Utilities
 * Simple functions to test API connectivity and service integration
 */

import { 
  deviceService, 
  containerService, 
  systemMetricsService, 
  proxyService,
  checkAPIHealth 
} from '@/services';

export async function testAPIConnectivity(): Promise<{
  status: 'connected' | 'error';
  message: string;
  details?: any;
}> {
  try {
    const isHealthy = await checkAPIHealth();
    
    if (isHealthy) {
      return {
        status: 'connected',
        message: 'API server is responding and healthy',
      };
    } else {
      return {
        status: 'error',
        message: 'API server health check failed',
      };
    }
  } catch (error) {
    return {
      status: 'error',
      message: `Failed to connect to API: ${error instanceof Error ? error.message : 'Unknown error'}`,
      details: error,
    };
  }
}

export async function testAPIServices(): Promise<{
  service: string;
  status: 'success' | 'error';
  message: string;
}[]> {
  const results: { service: string; status: 'success' | 'error'; message: string }[] = [];

  // Test Device Service
  try {
    await deviceService.list();
    results.push({
      service: 'deviceService',
      status: 'success',
      message: 'Successfully fetched device list',
    });
  } catch (error) {
    results.push({
      service: 'deviceService',
      status: 'error',
      message: `Device service error: ${error instanceof Error ? error.message : 'Unknown error'}`,
    });
  }

  // Test Container Service
  try {
    await containerService.list();
    results.push({
      service: 'containerService',
      status: 'success',
      message: 'Successfully fetched container list',
    });
  } catch (error) {
    results.push({
      service: 'containerService',
      status: 'error',
      message: `Container service error: ${error instanceof Error ? error.message : 'Unknown error'}`,
    });
  }

  // Test System Metrics Service
  try {
    await systemMetricsService.getHealth();
    results.push({
      service: 'systemMetricsService',
      status: 'success',
      message: 'Successfully fetched system health',
    });
  } catch (error) {
    results.push({
      service: 'systemMetricsService',
      status: 'error',
      message: `System metrics service error: ${error instanceof Error ? error.message : 'Unknown error'}`,
    });
  }

  // Test Proxy Service
  try {
    await proxyService.list();
    results.push({
      service: 'proxyService',
      status: 'success',
      message: 'Successfully fetched proxy configurations',
    });
  } catch (error) {
    results.push({
      service: 'proxyService',
      status: 'error',
      message: `Proxy service error: ${error instanceof Error ? error.message : 'Unknown error'}`,
    });
  }

  return results;
}

// Console helper for debugging
export function logAPITestResults() {
  console.log('🧪 Testing API Integration...');
  
  testAPIConnectivity().then(result => {
    console.log('🌐 API Connectivity:', result);
  });

  testAPIServices().then(results => {
    console.log('🔧 Service Tests:');
    results.forEach(result => {
      const emoji = result.status === 'success' ? '✅' : '❌';
      console.log(`${emoji} ${result.service}: ${result.message}`);
    });
  });
}

// Export for use in browser console during development
if (typeof window !== 'undefined') {
  (window as any).testAPI = {
    testConnectivity: testAPIConnectivity,
    testServices: testAPIServices,
    logResults: logAPITestResults,
  };
}
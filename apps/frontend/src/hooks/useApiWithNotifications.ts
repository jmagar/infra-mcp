/**
 * API Hook with Integrated Notifications
 * Provides comprehensive error handling and user feedback for API calls
 */

import { useState, useCallback } from 'react';
import { useNotifications } from '@/components/common';

interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

interface ApiOptions {
  successMessage?: string;
  errorMessage?: string;
  showSuccessNotification?: boolean;
  showErrorNotification?: boolean;
  loadingMessage?: string;
}

interface ApiHookReturn<T> extends ApiState<T> {
  execute: (apiCall: () => Promise<T>, options?: ApiOptions) => Promise<T>;
  reset: () => void;
  setData: (data: T | null) => void;
}

export function useApiWithNotifications<T = any>(
  defaultOptions?: ApiOptions
): ApiHookReturn<T> {
  const [state, setState] = useState<ApiState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  const notifications = useNotifications();

  const execute = useCallback(async (
    apiCall: () => Promise<T>,
    options: ApiOptions = {}
  ): Promise<T> => {
    const mergedOptions = { ...defaultOptions, ...options };
    const {
      successMessage,
      errorMessage = 'An error occurred',
      showSuccessNotification = true,
      showErrorNotification = true,
      loadingMessage = 'Processing...',
    } = mergedOptions;

    setState(prev => ({ ...prev, loading: true, error: null }));

    // Show loading notification for long operations
    let loadingNotificationId: string | null = null;
    const loadingTimeout = setTimeout(() => {
      loadingNotificationId = notifications.info(
        'Please wait',
        loadingMessage,
        { duration: 0, dismissible: false }
      );
    }, 1000);

    try {
      const result = await apiCall();
      
      setState({
        data: result,
        loading: false,
        error: null,
      });

      // Show success notification
      if (showSuccessNotification && successMessage) {
        notifications.success('Success', successMessage);
      }

      return result;
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      
      setState(prev => ({
        ...prev,
        loading: false,
        error: errorMsg,
      }));

      // Show error notification
      if (showErrorNotification) {
        const title = 'Operation Failed';
        const message = errorMessage === 'An error occurred' ? errorMsg : errorMessage;
        
        notifications.error(title, message, {
          action: {
            label: 'Retry',
            onClick: () => execute(apiCall, options),
          },
        });
      }

      throw error; // Re-throw for caller handling
    } finally {
      clearTimeout(loadingTimeout);
      if (loadingNotificationId) {
        notifications.removeNotification(loadingNotificationId);
      }
    }
  }, [notifications, defaultOptions]);

  const reset = useCallback(() => {
    setState({
      data: null,
      loading: false,
      error: null,
    });
  }, []);

  const setData = useCallback((data: T | null) => {
    setState(prev => ({ ...prev, data }));
  }, []);

  return {
    ...state,
    execute,
    reset,
    setData,
  };
}

// Specialized hooks for common patterns
export function useApiCall<T = any>(options?: ApiOptions) {
  return useApiWithNotifications<T>(options);
}

export function useApiMutation<TData = any, TVariables = any>(
  mutationFn: (variables: TVariables) => Promise<TData>,
  options: ApiOptions = {}
) {
  const api = useApiWithNotifications<TData>(options);

  const mutate = useCallback((variables: TVariables, mutationOptions?: ApiOptions) => {
    return api.execute(() => mutationFn(variables), mutationOptions);
  }, [api, mutationFn]);

  return {
    ...api,
    mutate,
  };
}

// Hook for batch operations with progress tracking
export function useBatchApi<T = any>(options?: ApiOptions) {
  const [progress, setProgress] = useState(0);
  const [completedItems, setCompletedItems] = useState<T[]>([]);
  const [failedItems, setFailedItems] = useState<Array<{ item: any; error: string }>>([]);
  const api = useApiWithNotifications<T[]>(options);

  const executeBatch = useCallback(async <TItem>(
    items: TItem[],
    batchFn: (item: TItem) => Promise<T>,
    batchOptions?: ApiOptions & { 
      batchSize?: number;
      showProgress?: boolean;
    }
  ): Promise<T[]> => {
    const { 
      batchSize = 5, 
      showProgress = true,
      ...apiOptions 
    } = batchOptions || {};

    setProgress(0);
    setCompletedItems([]);
    setFailedItems([]);

    let progressNotificationId: string | null = null;
    if (showProgress) {
      progressNotificationId = notifications.info(
        'Batch Operation',
        `Processing ${items.length} items...`,
        { duration: 0, dismissible: false }
      );
    }

    try {
      const results: T[] = [];
      
      // Process items in batches
      for (let i = 0; i < items.length; i += batchSize) {
        const batch = items.slice(i, i + batchSize);
        const batchPromises = batch.map(async (item, batchIndex) => {
          try {
            const result = await batchFn(item);
            setCompletedItems(prev => [...prev, result]);
            return result;
          } catch (error) {
            const errorMsg = error instanceof Error ? error.message : 'Unknown error';
            setFailedItems(prev => [...prev, { item, error: errorMsg }]);
            throw error;
          }
        });

        const batchResults = await Promise.allSettled(batchPromises);
        
        batchResults.forEach((result, batchIndex) => {
          if (result.status === 'fulfilled') {
            results.push(result.value);
          }
        });

        const newProgress = Math.round(((i + batch.length) / items.length) * 100);
        setProgress(newProgress);

        if (showProgress && progressNotificationId) {
          notifications.removeNotification(progressNotificationId);
          progressNotificationId = notifications.info(
            'Batch Operation',
            `Progress: ${newProgress}% (${Math.min(i + batch.length, items.length)}/${items.length})`,
            { duration: 0, dismissible: false }
          );
        }
      }

      // Show completion notification
      const successful = results.length;
      const failed = items.length - successful;

      if (failed === 0) {
        notifications.success(
          'Batch Complete',
          `Successfully processed all ${successful} items`
        );
      } else {
        notifications.warning(
          'Batch Completed with Errors',
          `${successful} items succeeded, ${failed} items failed`
        );
      }

      return results;
    } finally {
      if (progressNotificationId) {
        notifications.removeNotification(progressNotificationId);
      }
    }
  }, [notifications]);

  return {
    ...api,
    executeBatch,
    progress,
    completedItems,
    failedItems,
  };
}

// Global error handler that can be used anywhere
export function useGlobalErrorHandler() {
  const notifications = useNotifications();

  return useCallback((error: Error | string, context?: string) => {
    const message = typeof error === 'string' ? error : error.message;
    const title = context ? `${context} Error` : 'Unexpected Error';
    
    notifications.error(title, message, {
      duration: 8000,
      action: {
        label: 'Report',
        onClick: () => {
          // TODO: Implement error reporting
          console.log('Error reported:', { error, context });
        },
      },
    });
  }, [notifications]);
}
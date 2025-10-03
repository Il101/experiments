/**
 * Example custom hook with AbortSignal support
 * Demonstrates how to use cancellable requests with React Query
 */

import { useQuery, type UseQueryOptions } from '@tanstack/react-query';
import { useRef, useEffect } from 'react';
import { apiClient } from '../api/client';
import type { EngineStatus } from '../types';

/**
 * Hook for fetching engine status with automatic cancellation on unmount
 * React Query automatically cancels the request when the component unmounts
 */
export function useEngineStatusCancellable(options?: UseQueryOptions<EngineStatus>) {
  return useQuery<EngineStatus>({
    queryKey: ['engine', 'status'],
    queryFn: async ({ signal }) => {
      // React Query provides AbortSignal automatically
      // Pass it to the API client for cancellation support
      return apiClient.getCancellable<EngineStatus>('/api/engine/status', signal);
    },
    refetchInterval: 2000, // Poll every 2 seconds
    ...options,
  });
}

/**
 * Example: Long-running request with manual cancellation
 */
export function useLongRunningRequest(enabled: boolean = true) {
  return useQuery({
    queryKey: ['long-running'],
    queryFn: async ({ signal }) => {
      // This request can be cancelled manually or on unmount
      return apiClient.getCancellable('/api/some-long-endpoint', signal);
    },
    enabled,
    staleTime: Infinity, // Never refetch automatically
  });
}

/**
 * Example: Multiple requests with shared cancellation
 */
export function useMultipleRequestsCancellable() {
  const positions = useQuery({
    queryKey: ['trading', 'positions'],
    queryFn: ({ signal }) => 
      apiClient.getCancellable('/api/trading/positions', signal),
  });

  const orders = useQuery({
    queryKey: ['trading', 'orders'],
    queryFn: ({ signal }) => 
      apiClient.getCancellable('/api/trading/orders', signal),
  });

  return {
    positions,
    orders,
    isLoading: positions.isLoading || orders.isLoading,
    isError: positions.isError || orders.isError,
  };
}

/**
 * Manual cancellation example for imperative usage
 */
export function useManualCancellation() {
  const abortControllerRef = useRef<AbortController | null>(null);

  const fetchData = async (url: string) => {
    // Cancel previous request if exists
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new abort controller
    const controller = apiClient.createAbortController();
    abortControllerRef.current = controller;

    try {
      const data = await apiClient.getCancellable(url, controller.signal);
      return data;
    } catch (error) {
      if (error && typeof error === 'object' && 'name' in error && error.name === 'CanceledError') {
        console.log('Request was cancelled');
      }
      throw error;
    }
  };

  const cancelAll = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cancelAll();
    };
  }, []);

  return { fetchData, cancelAll };
}

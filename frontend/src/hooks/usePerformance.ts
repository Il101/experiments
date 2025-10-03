/**
 * React Query hooks для Performance API
 */

import { useQuery } from '@tanstack/react-query';
import { performanceApi } from '../api/endpoints';

// Query keys
export const performanceKeys = {
  all: ['performance'] as const,
  equity: (timeRange?: string) => [...performanceKeys.all, 'equity', timeRange] as const,
  metrics: () => [...performanceKeys.all, 'metrics'] as const,
  rDistribution: () => [...performanceKeys.all, 'r-distribution'] as const,
};

// Hooks
export const useEquityHistory = (timeRange?: string) => {
  return useQuery({
    queryKey: performanceKeys.equity(timeRange),
    queryFn: () => performanceApi.getEquityHistory(timeRange),
    refetchInterval: 60000, // Обновляем каждую минуту
    staleTime: 30000,
  });
};

export const usePerformanceMetrics = () => {
  return useQuery({
    queryKey: performanceKeys.metrics(),
    queryFn: performanceApi.getMetrics,
    refetchInterval: 30000, // Обновляем каждые 30 секунд
    staleTime: 15000,
  });
};

export const useRDistribution = () => {
  return useQuery({
    queryKey: performanceKeys.rDistribution(),
    queryFn: performanceApi.getRDistribution,
    refetchInterval: 120000, // Обновляем каждые 2 минуты
    staleTime: 60000,
  });
};



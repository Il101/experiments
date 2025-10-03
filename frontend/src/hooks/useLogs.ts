/**
 * React Query hooks для Logs API
 */

import { useQuery } from '@tanstack/react-query';
import { logsApi } from '../api/endpoints';
import type { LogsQuery } from '../types';

// Query keys
export const logsKeys = {
  all: ['logs'] as const,
  list: (query: LogsQuery) => [...logsKeys.all, 'list', query] as const,
};

// Hooks
export const useLogs = (query: LogsQuery = {}) => {
  return useQuery({
    queryKey: logsKeys.list(query),
    queryFn: () => logsApi.getLogs(query),
    refetchInterval: 10000, // Обновляем каждые 10 секунд
    staleTime: 5000,
  });
};



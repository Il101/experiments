/**
 * React Query hooks для Engine API
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { engineApi } from '../api/endpoints';

// Query keys
export const engineKeys = {
  all: ['engine'] as const,
  status: () => [...engineKeys.all, 'status'] as const,
  metrics: () => [...engineKeys.all, 'metrics'] as const,
  commands: () => [...engineKeys.all, 'commands'] as const,
};

// Hooks
export const useEngineStatus = () => {
  return useQuery({
    queryKey: engineKeys.status(),
    queryFn: engineApi.getStatus,
    refetchInterval: 5000, // Обновляем каждые 5 секунд
    staleTime: 3000, // Данные считаются свежими 3 секунды
  });
};

export const useEngineMetrics = () => {
  return useQuery({
    queryKey: engineKeys.metrics(),
    queryFn: engineApi.getMetrics,
    refetchInterval: 10000, // Обновляем каждые 10 секунд
    staleTime: 5000,
  });
};

export const useStartEngine = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: engineApi.start,
    onSuccess: () => {
      // Инвалидируем кэш статуса и метрик
      queryClient.invalidateQueries({ queryKey: engineKeys.status() });
      queryClient.invalidateQueries({ queryKey: engineKeys.metrics() });
    },
  });
};

export const useStopEngine = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: engineApi.stop,
    onSuccess: () => {
      // Инвалидируем кэш статуса и метрик
      queryClient.invalidateQueries({ queryKey: engineKeys.status() });
      queryClient.invalidateQueries({ queryKey: engineKeys.metrics() });
    },
  });
};

export const useReloadEngine = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: engineApi.reload,
    onSuccess: () => {
      // Инвалидируем все кэши
      queryClient.invalidateQueries({ queryKey: engineKeys.all });
    },
  });
};

export const useEngineCommands = () => {
  return useQuery({
    queryKey: engineKeys.commands(),
    queryFn: engineApi.getCommands,
    refetchInterval: 5000, // 5 seconds
  });
};

export const useExecuteCommand = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: engineApi.executeCommand,
    onSuccess: () => {
      // Инвалидируем кэш статуса и команд
      queryClient.invalidateQueries({ queryKey: engineKeys.status() });
      queryClient.invalidateQueries({ queryKey: engineKeys.commands() });
    },
  });
};

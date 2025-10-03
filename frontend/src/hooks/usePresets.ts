/**
 * React Query hooks для Presets API
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { presetsApi } from '../api/endpoints';

// Query keys
export const presetsKeys = {
  all: ['presets'] as const,
  list: () => [...presetsKeys.all, 'list'] as const,
  preset: (name: string) => [...presetsKeys.all, 'preset', name] as const,
};

// Hooks
export const usePresets = () => {
  return useQuery({
    queryKey: presetsKeys.list(),
    queryFn: presetsApi.getPresets,
    staleTime: 300000, // 5 минут - пресеты редко меняются
  });
};

export const usePreset = (name: string) => {
  return useQuery({
    queryKey: presetsKeys.preset(name),
    queryFn: () => presetsApi.getPreset(name),
    enabled: !!name,
    staleTime: 300000,
  });
};

export const useUpdatePreset = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ name, config }: { name: string; config: Record<string, any> }) =>
      presetsApi.updatePreset(name, config),
    onSuccess: (_, { name }) => {
      // Инвалидируем кэш конкретного пресета и списка
      queryClient.invalidateQueries({ queryKey: presetsKeys.preset(name) });
      queryClient.invalidateQueries({ queryKey: presetsKeys.list() });
    },
  });
};



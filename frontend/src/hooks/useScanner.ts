/**
 * React Query hooks для Scanner API
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { scannerApi } from '../api/endpoints';

// Query keys
export const scannerKeys = {
  all: ['scanner'] as const,
  lastScan: () => [...scannerKeys.all, 'last'] as const,
};

// Hooks
export const useLastScan = () => {
  return useQuery({
    queryKey: scannerKeys.lastScan(),
    queryFn: scannerApi.getLastScan,
    refetchInterval: 30000, // Обновляем каждые 30 секунд
    staleTime: 15000,
  });
};

export const useScanMarket = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: scannerApi.scanMarket,
    onSuccess: () => {
      // Инвалидируем кэш последнего сканирования
      queryClient.invalidateQueries({ queryKey: scannerKeys.lastScan() });
    },
  });
};

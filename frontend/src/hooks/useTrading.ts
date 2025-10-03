/**
 * React Query hooks для Trading API
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { tradingApi } from '../api/endpoints';

// Query keys
export const tradingKeys = {
  all: ['trading'] as const,
  positions: () => [...tradingKeys.all, 'positions'] as const,
  position: (id: string) => [...tradingKeys.positions(), id] as const,
  orders: () => [...tradingKeys.all, 'orders'] as const,
};

// Hooks
export const usePositions = () => {
  return useQuery({
    queryKey: tradingKeys.positions(),
    queryFn: tradingApi.getPositions,
    refetchInterval: 10000, // Обновляем каждые 10 секунд
    staleTime: 5000,
  });
};

export const usePosition = (id: string) => {
  return useQuery({
    queryKey: tradingKeys.position(id),
    queryFn: () => tradingApi.getPosition(id),
    enabled: !!id,
  });
};

export const useOrders = () => {
  return useQuery({
    queryKey: tradingKeys.orders(),
    queryFn: tradingApi.getOrders,
    refetchInterval: 15000, // Обновляем каждые 15 секунд
    staleTime: 10000,
  });
};

export const useCancelOrder = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: tradingApi.cancelOrder,
    onSuccess: () => {
      // Инвалидируем кэш ордеров
      queryClient.invalidateQueries({ queryKey: tradingKeys.orders() });
    },
  });
};



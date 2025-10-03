/**
 * React Query hooks для Charts API
 */

import { useQuery } from '@tanstack/react-query';
import { chartsApi } from '../api/endpoints';

// Query keys
export const chartsKeys = {
  all: ['charts'] as const,
  candles: (symbol: string, timeframe: string) => [...chartsKeys.all, 'candles', symbol, timeframe] as const,
  levels: (symbol: string) => [...chartsKeys.all, 'levels', symbol] as const,
};

// Hooks
export const useCandles = (symbol: string, timeframe: string = '15m') => {
  return useQuery({
    queryKey: chartsKeys.candles(symbol, timeframe),
    queryFn: () => chartsApi.getCandles(symbol, timeframe),
    refetchInterval: 60000, // Обновляем каждую минуту
    staleTime: 30000,
    enabled: !!symbol,
  });
};

export const useLevels = (symbol: string) => {
  return useQuery({
    queryKey: chartsKeys.levels(symbol),
    queryFn: () => chartsApi.getLevels(symbol),
    refetchInterval: 120000, // Обновляем каждые 2 минуты
    staleTime: 60000,
    enabled: !!symbol,
  });
};



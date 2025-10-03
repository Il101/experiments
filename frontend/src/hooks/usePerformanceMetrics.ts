/**
 * usePerformanceMetrics Hook
 * React Query hook for performance analytics
 */

import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import type { PerformanceMetrics, DrawdownAnalysis } from '../types/analytics';
import { calculatePerformanceMetrics } from '../utils/performanceCalculator';
import { analyzeDrawdowns } from '../utils/drawdownAnalyzer';

// ==================== Interfaces ====================

interface Trade {
  id: string;
  symbol: string;
  side: 'long' | 'short';
  entryPrice: number;
  exitPrice?: number;
  size: number;
  entryTime: string;
  exitTime?: string;
  pnl: number;
  pnlPercent: number;
  rMultiple?: number;
  stopLoss?: number;
  takeProfit?: number;
  status: 'open' | 'closed';
}

interface Position {
  symbol: string;
  side: 'long' | 'short';
  size: number;
  entryPrice: number;
  currentPrice: number;
  unrealizedPnl: number;
  unrealizedPnlPercent: number;
}

interface EquityPoint {
  timestamp: string;
  date: Date;
  equity: number;
  pnl: number;
  tradeId?: string;
}

interface UsePerformanceMetricsOptions {
  trades: Trade[];
  positions?: Position[];
  startingEquity?: number;
  enabled?: boolean;
  refetchInterval?: number;
}

interface UsePerformanceMetricsReturn {
  metrics: PerformanceMetrics | undefined;
  drawdowns: DrawdownAnalysis | undefined;
  equityCurve: EquityPoint[];
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  refetch: () => void;
}

// ==================== Hook ====================

/**
 * Hook for calculating performance metrics
 * 
 * @example
 * ```tsx
 * const { metrics, drawdowns, equityCurve, isLoading } = usePerformanceMetrics({
 *   trades: closedTrades,
 *   positions: openPositions,
 *   startingEquity: 10000,
 * });
 * 
 * if (isLoading) return <Spinner />;
 * 
 * return (
 *   <div>
 *     <div>Win Rate: {metrics.winRate.toFixed(1)}%</div>
 *     <div>Profit Factor: {metrics.profitFactor.toFixed(2)}</div>
 *     <div>Max Drawdown: {metrics.maxDrawdown.toFixed(1)}%</div>
 *   </div>
 * );
 * ```
 */
export function usePerformanceMetrics(
  options: UsePerformanceMetricsOptions
): UsePerformanceMetricsReturn {
  const {
    trades,
    positions = [],
    startingEquity = 10000,
    enabled = true,
    refetchInterval,
  } = options;

  // Build equity curve
  const equityCurve = useMemo(() => {
    return buildEquityCurve(trades, startingEquity);
  }, [trades, startingEquity]);

  // Calculate metrics
  const {
    data: metrics,
    isLoading: metricsLoading,
    isError: metricsError,
    error: metricsErrorObj,
    refetch: refetchMetrics,
  } = useQuery({
    queryKey: ['performance-metrics', trades, positions, startingEquity],
    queryFn: () => calculatePerformanceMetrics(trades, positions, startingEquity),
    enabled,
    refetchInterval,
    staleTime: 30000, // 30 seconds
  });

  // Analyze drawdowns
  const {
    data: drawdowns,
    isLoading: drawdownsLoading,
    isError: drawdownsError,
    error: drawdownsErrorObj,
    refetch: refetchDrawdowns,
  } = useQuery({
    queryKey: ['drawdown-analysis', equityCurve, startingEquity],
    queryFn: () => analyzeDrawdowns(equityCurve, startingEquity),
    enabled: enabled && equityCurve.length > 0,
    refetchInterval,
    staleTime: 30000,
  });

  const refetch = () => {
    refetchMetrics();
    refetchDrawdowns();
  };

  return {
    metrics,
    drawdowns,
    equityCurve,
    isLoading: metricsLoading || drawdownsLoading,
    isError: metricsError || drawdownsError,
    error: (metricsErrorObj || drawdownsErrorObj) as Error | null,
    refetch,
  };
}

// ==================== Helper Functions ====================

/**
 * Build equity curve from trades
 */
function buildEquityCurve(trades: Trade[], startingEquity: number): EquityPoint[] {
  let equity = startingEquity;
  const points: EquityPoint[] = [
    {
      timestamp: trades[0]?.entryTime || new Date().toISOString(),
      date: new Date(trades[0]?.entryTime || new Date()),
      equity,
      pnl: 0,
    },
  ];

  const closedTrades = trades
    .filter(t => t.status === 'closed' && t.exitTime)
    .sort((a, b) => new Date(a.exitTime!).getTime() - new Date(b.exitTime!).getTime());

  closedTrades.forEach(trade => {
    equity += trade.pnl;
    points.push({
      timestamp: trade.exitTime!,
      date: new Date(trade.exitTime!),
      equity,
      pnl: trade.pnl,
      tradeId: trade.id,
    });
  });

  return points;
}

// ==================== Specialized Hooks ====================

/**
 * Hook for getting just the key metrics
 */
export function useKeyMetrics(
  trades: Trade[],
  positions: Position[] = [],
  startingEquity: number = 10000
) {
  const { metrics, isLoading } = usePerformanceMetrics({
    trades,
    positions,
    startingEquity,
  });

  return {
    winRate: metrics?.winRate ?? 0,
    profitFactor: metrics?.profitFactor ?? 0,
    sharpeRatio: metrics?.sharpeRatio ?? 0,
    maxDrawdown: metrics?.maxDrawdown ?? 0,
    totalPnL: metrics?.totalPnL ?? 0,
    isLoading,
  };
}

/**
 * Hook for getting current drawdown status
 */
export function useCurrentDrawdown(
  trades: Trade[],
  startingEquity: number = 10000
) {
  const { drawdowns, isLoading } = usePerformanceMetrics({
    trades,
    startingEquity,
  });

  const currentDrawdown = drawdowns?.currentDrawdown;

  return {
    isInDrawdown: currentDrawdown !== null,
    drawdownPercent: currentDrawdown?.drawdownPercent ?? 0,
    daysInDrawdown: currentDrawdown?.durationDays ?? 0,
    distanceFromPeak: currentDrawdown ? Math.abs(currentDrawdown.drawdownPercent) : 0,
    isLoading,
  };
}

/**
 * Hook for getting performance grade
 */
export function usePerformanceGrade(
  trades: Trade[],
  startingEquity: number = 10000
) {
  const { metrics, isLoading } = usePerformanceMetrics({
    trades,
    startingEquity,
  });

  return {
    grade: metrics?.overallGrade ?? 'F',
    score: metrics?.gradeScore ?? 0,
    isLoading,
  };
}

/**
 * Hook for comparing two time periods
 */
export function usePerformanceComparison(
  currentTrades: Trade[],
  previousTrades: Trade[],
  startingEquity: number = 10000
) {
  const current = usePerformanceMetrics({
    trades: currentTrades,
    startingEquity,
  });

  const previous = usePerformanceMetrics({
    trades: previousTrades,
    startingEquity,
  });

  const comparison = useMemo(() => {
    if (!current.metrics || !previous.metrics) return null;

    const changes = {
      totalPnL: current.metrics.totalPnL - previous.metrics.totalPnL,
      winRate: current.metrics.winRate - previous.metrics.winRate,
      profitFactor: current.metrics.profitFactor - previous.metrics.profitFactor,
      sharpeRatio: current.metrics.sharpeRatio - previous.metrics.sharpeRatio,
      maxDrawdown: current.metrics.maxDrawdown - previous.metrics.maxDrawdown,
    };

    const percentChanges = {
      totalPnL: previous.metrics.totalPnL !== 0
        ? ((current.metrics.totalPnL - previous.metrics.totalPnL) / Math.abs(previous.metrics.totalPnL)) * 100
        : 0,
      winRate: previous.metrics.winRate !== 0
        ? ((current.metrics.winRate - previous.metrics.winRate) / previous.metrics.winRate) * 100
        : 0,
      profitFactor: previous.metrics.profitFactor !== 0
        ? ((current.metrics.profitFactor - previous.metrics.profitFactor) / previous.metrics.profitFactor) * 100
        : 0,
      sharpeRatio: previous.metrics.sharpeRatio !== 0
        ? ((current.metrics.sharpeRatio - previous.metrics.sharpeRatio) / previous.metrics.sharpeRatio) * 100
        : 0,
      maxDrawdown: previous.metrics.maxDrawdown !== 0
        ? ((current.metrics.maxDrawdown - previous.metrics.maxDrawdown) / Math.abs(previous.metrics.maxDrawdown)) * 100
        : 0,
    };

    // Determine overall trend
    let trend: 'improving' | 'declining' | 'stable' = 'stable';
    const improvementScore = 
      (changes.winRate > 0 ? 1 : -1) +
      (changes.profitFactor > 0 ? 1 : -1) +
      (changes.sharpeRatio > 0 ? 1 : -1) +
      (changes.maxDrawdown > 0 ? -1 : 1); // Lower drawdown is better

    if (improvementScore >= 2) trend = 'improving';
    else if (improvementScore <= -2) trend = 'declining';

    return {
      current: current.metrics,
      previous: previous.metrics,
      changes,
      percentChanges,
      trend,
    };
  }, [current.metrics, previous.metrics]);

  return {
    comparison,
    isLoading: current.isLoading || previous.isLoading,
    isError: current.isError || previous.isError,
  };
}

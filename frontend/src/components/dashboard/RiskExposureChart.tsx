/**
 * Risk Exposure Chart Component
 * Visualizes portfolio risk distribution and exposure
 */

import React, { useMemo } from 'react';
import { Shield, AlertTriangle } from 'lucide-react';
import { useRealTimePrices } from '../../hooks/useRealTimePrices';
import type { Position } from '../../types';

interface RiskExposureChartProps {
  positions: Position[];
  className?: string;
}

interface RiskMetrics {
  symbol: string;
  side: 'long' | 'short';
  exposure: number; // USD value at risk
  exposurePercent: number; // % of total portfolio
  stopLossDistance: number; // % distance to stop loss
  riskAmount: number; // Potential loss in USD
  currentPnL: number;
  isAtRisk: boolean; // Price near stop loss
}

const formatCurrency = (value: number): string => {
  if (Math.abs(value) >= 1000000) {
    return `$${(value / 1000000).toFixed(2)}M`;
  }
  if (Math.abs(value) >= 1000) {
    return `$${(value / 1000).toFixed(1)}K`;
  }
  return `$${value.toFixed(0)}`;
};

const RiskBar: React.FC<{ metrics: RiskMetrics }> = ({ metrics }) => {
  const isLong = metrics.side === 'long';
  const barColor = metrics.isAtRisk
    ? 'bg-red-500'
    : metrics.currentPnL >= 0
    ? 'bg-green-500'
    : 'bg-yellow-500';

  return (
    <div className="mb-3">
      {/* Header */}
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm text-gray-900 dark:text-gray-100">
            {metrics.symbol}
          </span>
          <span
            className={`
              text-xs px-1.5 py-0.5 rounded font-medium
              ${isLong ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'}
            `}
          >
            {isLong ? 'LONG' : 'SHORT'}
          </span>
          {metrics.isAtRisk && (
            <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
          )}
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className="text-gray-500 dark:text-gray-400">
            {metrics.exposurePercent.toFixed(1)}%
          </span>
          <span className="font-mono text-gray-900 dark:text-gray-100">
            {formatCurrency(metrics.exposure)}
          </span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="relative h-8 bg-gray-100 dark:bg-gray-800 rounded-lg overflow-hidden">
        <div
          className={`
            absolute inset-y-0 left-0 ${barColor} transition-all duration-500
            flex items-center justify-between px-3
          `}
          style={{ width: `${metrics.exposurePercent}%` }}
        >
          <span className="text-xs font-medium text-white">
            {metrics.stopLossDistance.toFixed(1)}% to SL
          </span>
          {metrics.exposurePercent > 20 && (
            <span className="text-xs font-mono text-white">
              Risk: {formatCurrency(metrics.riskAmount)}
            </span>
          )}
        </div>
        
        {/* Show risk amount outside bar if bar is too small */}
        {metrics.exposurePercent <= 20 && (
          <div className="absolute inset-y-0 right-0 flex items-center pr-3">
            <span className="text-xs font-mono text-gray-600 dark:text-gray-400">
              Risk: {formatCurrency(metrics.riskAmount)}
            </span>
          </div>
        )}
      </div>

      {/* Current P&L indicator */}
      <div className="flex justify-end mt-1">
        <span
          className={`
            text-xs font-mono
            ${metrics.currentPnL >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}
          `}
        >
          P&L: {metrics.currentPnL >= 0 ? '+' : ''}{formatCurrency(metrics.currentPnL)}
        </span>
      </div>
    </div>
  );
};

export const RiskExposureChart: React.FC<RiskExposureChartProps> = ({ positions, className = '' }) => {
  const { positionPnLs, getTotalPnL } = useRealTimePrices(positions);
  const totalPnL = getTotalPnL();

  const riskMetrics = useMemo((): RiskMetrics[] => {
    if (positions.length === 0 || positionPnLs.length === 0) return [];

    // Calculate total portfolio exposure
    const totalExposure = positions.reduce(
      (sum, p) => sum + Math.abs(p.currentPrice || p.entry) * p.size,
      0
    );

    return positions
      .map((position) => {
        const pnl = positionPnLs.find((p) => p.positionId === position.id);
        const currentPrice = pnl?.currentPrice || position.currentPrice || position.entry;
        const exposure = Math.abs(currentPrice * position.size);
        const exposurePercent = totalExposure > 0 ? (exposure / totalExposure) * 100 : 0;

        // Calculate distance to stop loss
        const isLong = position.side === 'long';
        const stopLossDistance = isLong
          ? ((currentPrice - position.sl) / currentPrice) * 100
          : ((position.sl - currentPrice) / currentPrice) * 100;

        // Calculate risk amount (potential loss)
        const riskAmount = Math.abs((currentPrice - position.sl) * position.size);

        // Check if position is at risk (within 10% of stop loss)
        const isAtRisk = stopLossDistance < 10 && stopLossDistance > 0;

        return {
          symbol: position.symbol,
          side: position.side,
          exposure,
          exposurePercent,
          stopLossDistance,
          riskAmount,
          currentPnL: pnl?.unrealizedPnL || 0,
          isAtRisk,
        };
      })
      .sort((a, b) => b.exposure - a.exposure); // Sort by exposure descending
  }, [positions, positionPnLs]);

  const portfolioStats = useMemo(() => {
    const totalExposure = riskMetrics.reduce((sum, m) => sum + m.exposure, 0);
    const totalRisk = riskMetrics.reduce((sum, m) => sum + m.riskAmount, 0);
    const longExposure = riskMetrics
      .filter((m) => m.side === 'long')
      .reduce((sum, m) => sum + m.exposure, 0);
    const shortExposure = riskMetrics
      .filter((m) => m.side === 'short')
      .reduce((sum, m) => sum + m.exposure, 0);
    const atRiskCount = riskMetrics.filter((m) => m.isAtRisk).length;

    return {
      totalExposure,
      totalRisk,
      longExposure,
      shortExposure,
      longPercent: totalExposure > 0 ? (longExposure / totalExposure) * 100 : 0,
      shortPercent: totalExposure > 0 ? (shortExposure / totalExposure) * 100 : 0,
      atRiskCount,
      riskRewardRatio: totalRisk > 0 ? Math.abs(totalPnL.unrealized / totalRisk) : 0,
    };
  }, [riskMetrics, totalPnL]);

  if (positions.length === 0) {
    return (
      <div className={`bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6 ${className}`}>
        <div className="text-center text-gray-500 dark:text-gray-400">
          <Shield className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No positions to analyze</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <Shield className="w-5 h-5 text-blue-500" />
            Risk Exposure
          </h3>
          {portfolioStats.atRiskCount > 0 && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded-lg text-xs font-medium">
              <AlertTriangle className="w-3.5 h-3.5" />
              {portfolioStats.atRiskCount} at risk
            </div>
          )}
        </div>

        {/* Portfolio Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
              Total Exposure
            </div>
            <div className="font-mono font-semibold text-gray-900 dark:text-gray-100">
              {formatCurrency(portfolioStats.totalExposure)}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
              Total Risk
            </div>
            <div className="font-mono font-semibold text-red-600 dark:text-red-400">
              {formatCurrency(portfolioStats.totalRisk)}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
              Long / Short
            </div>
            <div className="font-mono font-semibold text-gray-900 dark:text-gray-100 text-sm">
              {portfolioStats.longPercent.toFixed(0)}% / {portfolioStats.shortPercent.toFixed(0)}%
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
              Risk/Reward
            </div>
            <div className={`font-mono font-semibold ${portfolioStats.riskRewardRatio >= 1 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
              {portfolioStats.riskRewardRatio.toFixed(2)}R
            </div>
          </div>
        </div>

        {/* Long/Short Balance Bar */}
        <div className="mt-4">
          <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
            <span>Portfolio Balance</span>
            <span>{formatCurrency(portfolioStats.totalExposure)}</span>
          </div>
          <div className="relative h-6 bg-gray-100 dark:bg-gray-800 rounded-lg overflow-hidden">
            <div
              className="absolute inset-y-0 left-0 bg-green-500 flex items-center justify-center text-white text-xs font-medium"
              style={{ width: `${portfolioStats.longPercent}%` }}
            >
              {portfolioStats.longPercent > 15 && `${portfolioStats.longPercent.toFixed(0)}% LONG`}
            </div>
            <div
              className="absolute inset-y-0 right-0 bg-red-500 flex items-center justify-center text-white text-xs font-medium"
              style={{ width: `${portfolioStats.shortPercent}%` }}
            >
              {portfolioStats.shortPercent > 15 && `${portfolioStats.shortPercent.toFixed(0)}% SHORT`}
            </div>
          </div>
        </div>
      </div>

      {/* Risk Bars */}
      <div className="p-4 max-h-[500px] overflow-y-auto custom-scrollbar">
        {riskMetrics.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400 text-sm">
            Waiting for position data...
          </div>
        ) : (
          <div>
            {riskMetrics.map((metrics, index) => (
              <RiskBar key={`${metrics.symbol}-${index}`} metrics={metrics} />
            ))}
          </div>
        )}
      </div>

      {/* Footer Legend */}
      <div className="px-4 pb-4 border-t border-gray-200 dark:border-gray-700 pt-3">
        <div className="flex items-center justify-center gap-4 text-xs text-gray-500 dark:text-gray-400">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded bg-green-500" />
            <span>Winning</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded bg-yellow-500" />
            <span>Losing</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded bg-red-500" />
            <span>At Risk (&lt;10% to SL)</span>
          </div>
        </div>
      </div>
    </div>
  );
};

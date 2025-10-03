/**
 * TradeDistributionChart Component
 * Histogram showing distribution of trade P&L results
 */

import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
} from 'recharts';
import { TrendingUp, TrendingDown, Target } from 'lucide-react';

// ==================== Interfaces ====================

interface TradeDistributionChartProps {
  trades: Array<{
    id: string;
    pnl: number;
    pnlPercent: number;
  }>;
  binCount?: number;
  height?: number;
  className?: string;
}

interface BinData {
  range: string;
  count: number;
  minPnl: number;
  maxPnl: number;
  percentage: number;
  isWinning: boolean;
}

// ==================== Component ====================

export const TradeDistributionChart: React.FC<TradeDistributionChartProps> = ({
  trades,
  binCount = 10,
  height = 350,
  className = '',
}) => {
  // Calculate histogram bins
  const { bins, stats } = React.useMemo(() => {
    if (trades.length === 0) {
      return {
        bins: [],
        stats: {
          mean: 0,
          median: 0,
          stdDev: 0,
          skewness: 0,
          winners: 0,
          losers: 0,
          maxWin: 0,
          maxLoss: 0,
        },
      };
    }

    const pnls = trades.map(t => t.pnl).sort((a, b) => a - b);
    const minPnl = pnls[0];
    const maxPnl = pnls[pnls.length - 1];
    const range = maxPnl - minPnl;
    const binSize = range / binCount;

    // Create bins
    const binsArray: BinData[] = [];
    for (let i = 0; i < binCount; i++) {
      const binMin = minPnl + i * binSize;
      const binMax = binMin + binSize;
      const tradesInBin = pnls.filter(p => p >= binMin && (i === binCount - 1 ? p <= binMax : p < binMax));
      
      binsArray.push({
        range: `${binMin.toFixed(0)} to ${binMax.toFixed(0)}`,
        count: tradesInBin.length,
        minPnl: binMin,
        maxPnl: binMax,
        percentage: (tradesInBin.length / trades.length) * 100,
        isWinning: binMax > 0,
      });
    }

    // Calculate statistics
    const mean = pnls.reduce((sum, p) => sum + p, 0) / pnls.length;
    const median = pnls[Math.floor(pnls.length / 2)];
    const variance = pnls.reduce((sum, p) => sum + Math.pow(p - mean, 2), 0) / pnls.length;
    const stdDev = Math.sqrt(variance);
    const skewness = pnls.reduce((sum, p) => sum + Math.pow((p - mean) / stdDev, 3), 0) / pnls.length;
    
    const winners = pnls.filter(p => p > 0).length;
    const losers = pnls.filter(p => p < 0).length;
    const maxWin = Math.max(...pnls);
    const maxLoss = Math.min(...pnls);

    return {
      bins: binsArray,
      stats: {
        mean,
        median,
        stdDev,
        skewness,
        winners,
        losers,
        maxWin,
        maxLoss,
      },
    };
  }, [trades, binCount]);

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || payload.length === 0) return null;

    const data = payload[0].payload as BinData;

    return (
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3">
        <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">
          P&L Range
        </div>
        <div className="space-y-1">
          <div className="flex items-center justify-between gap-4">
            <span className="text-sm text-gray-600 dark:text-gray-400">Range:</span>
            <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              ${data.minPnl.toFixed(0)} to ${data.maxPnl.toFixed(0)}
            </span>
          </div>
          <div className="flex items-center justify-between gap-4">
            <span className="text-sm text-gray-600 dark:text-gray-400">Trades:</span>
            <span className="text-sm font-semibold text-blue-600 dark:text-blue-400">
              {data.count} ({data.percentage.toFixed(1)}%)
            </span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className={`bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6 ${className}`}>
      {/* Header */}
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-1">
          <Target className="w-5 h-5 text-blue-500" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Trade Distribution
          </h3>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Histogram of P&L results
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Mean</div>
          <div className={`text-lg font-bold ${
            stats.mean >= 0 
              ? 'text-green-600 dark:text-green-400' 
              : 'text-red-600 dark:text-red-400'
          }`}>
            ${stats.mean.toFixed(2)}
          </div>
        </div>

        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Median</div>
          <div className={`text-lg font-bold ${
            stats.median >= 0 
              ? 'text-green-600 dark:text-green-400' 
              : 'text-red-600 dark:text-red-400'
          }`}>
            ${stats.median.toFixed(2)}
          </div>
        </div>

        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Std Dev</div>
          <div className="text-lg font-bold text-gray-900 dark:text-gray-100">
            ${stats.stdDev.toFixed(2)}
          </div>
        </div>

        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Skewness</div>
          <div className={`text-lg font-bold ${
            Math.abs(stats.skewness) < 0.5 
              ? 'text-green-600 dark:text-green-400' 
              : 'text-yellow-600 dark:text-yellow-400'
          }`}>
            {stats.skewness.toFixed(2)}
          </div>
        </div>
      </div>

      {/* Winners vs Losers */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp className="w-4 h-4 text-green-600 dark:text-green-400" />
            <span className="text-xs text-green-600 dark:text-green-400 font-semibold">
              Winners
            </span>
          </div>
          <div className="text-2xl font-bold text-green-600 dark:text-green-400">
            {stats.winners}
          </div>
          <div className="text-xs text-green-600 dark:text-green-400 mt-1">
            Max: ${stats.maxWin.toFixed(2)}
          </div>
        </div>

        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <TrendingDown className="w-4 h-4 text-red-600 dark:text-red-400" />
            <span className="text-xs text-red-600 dark:text-red-400 font-semibold">
              Losers
            </span>
          </div>
          <div className="text-2xl font-bold text-red-600 dark:text-red-400">
            {stats.losers}
          </div>
          <div className="text-xs text-red-600 dark:text-red-400 mt-1">
            Max: ${stats.maxLoss.toFixed(2)}
          </div>
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={bins} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.1} />
          
          <XAxis
            dataKey="range"
            stroke="#6b7280"
            fontSize={10}
            tickLine={false}
            angle={-45}
            textAnchor="end"
            height={80}
          />
          
          <YAxis
            stroke="#6b7280"
            fontSize={12}
            tickLine={false}
            label={{ value: 'Frequency', angle: -90, position: 'insideLeft', style: { fill: '#6b7280' } }}
          />
          
          <Tooltip content={<CustomTooltip />} />
          
          {/* Zero line */}
          <ReferenceLine
            y={0}
            stroke="#6b7280"
            strokeWidth={1}
          />

          {/* Mean line */}
          <ReferenceLine
            x={bins.find(b => stats.mean >= b.minPnl && stats.mean < b.maxPnl)?.range}
            stroke="#3b82f6"
            strokeDasharray="3 3"
            label={{ value: 'Mean', position: 'top', fill: '#3b82f6', fontSize: 12 }}
          />

          {/* Bars */}
          <Bar
            dataKey="count"
            radius={[4, 4, 0, 0]}
          >
            {bins.map((bin, index) => (
              <Cell 
                key={`cell-${index}`} 
                fill={bin.isWinning ? '#10b981' : '#ef4444'}
                opacity={0.8}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Distribution Info */}
      <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
        <div className="text-sm text-blue-900 dark:text-blue-100">
          <strong>Distribution Analysis:</strong>
          {Math.abs(stats.skewness) < 0.5 ? (
            <span className="ml-2">✓ Symmetric distribution (balanced wins/losses)</span>
          ) : stats.skewness > 0 ? (
            <span className="ml-2">⚠ Right-skewed (few large winners)</span>
          ) : (
            <span className="ml-2">⚠ Left-skewed (few large losers)</span>
          )}
        </div>
      </div>
    </div>
  );
};

/**
 * SymbolPerformanceChart Component
 * Bar chart comparing performance across different symbols
 */

import React, { useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { TrendingUp, TrendingDown, Target, ArrowUpDown } from 'lucide-react';
import type { SymbolPerformance } from '../../types/analytics';

// ==================== Interfaces ====================

interface SymbolPerformanceChartProps {
  symbolStats: SymbolPerformance[];
  height?: number;
  className?: string;
}

type SortKey = 'symbol' | 'trades' | 'winRate' | 'totalPnL' | 'profitFactor' | 'sharpeRatio';
type SortOrder = 'asc' | 'desc';

// ==================== Component ====================

export const SymbolPerformanceChart: React.FC<SymbolPerformanceChartProps> = ({
  symbolStats,
  height = 400,
  className = '',
}) => {
  const [sortKey, setSortKey] = useState<SortKey>('totalPnL');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [viewMode, setViewMode] = useState<'chart' | 'table'>('chart');

  // Sort data
  const sortedData = React.useMemo(() => {
    return [...symbolStats].sort((a, b) => {
      const multiplier = sortOrder === 'asc' ? 1 : -1;
      
      switch (sortKey) {
        case 'symbol':
          return multiplier * a.symbol.localeCompare(b.symbol);
        case 'trades':
          return multiplier * (a.trades - b.trades);
        case 'winRate':
          return multiplier * (a.winRate - b.winRate);
        case 'totalPnL':
          return multiplier * (a.totalPnL - b.totalPnL);
        case 'profitFactor':
          return multiplier * (a.profitFactor - b.profitFactor);
        case 'sharpeRatio':
          return multiplier * (a.sharpeRatio - b.sharpeRatio);
        default:
          return 0;
      }
    });
  }, [symbolStats, sortKey, sortOrder]);

  // Toggle sort
  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortOrder('desc');
    }
  };

  // Calculate aggregate stats
  const aggregateStats = React.useMemo(() => {
    const totalTrades = symbolStats.reduce((sum, s) => sum + s.trades, 0);
    const totalPnL = symbolStats.reduce((sum, s) => sum + s.totalPnL, 0);
    const avgWinRate = symbolStats.length > 0
      ? symbolStats.reduce((sum, s) => sum + s.winRate, 0) / symbolStats.length
      : 0;
    const bestSymbol = symbolStats.reduce((best, s) => 
      s.totalPnL > best.totalPnL ? s : best
    , symbolStats[0] || null);
    const worstSymbol = symbolStats.reduce((worst, s) => 
      s.totalPnL < worst.totalPnL ? s : worst
    , symbolStats[0] || null);

    return {
      totalTrades,
      totalPnL,
      avgWinRate,
      bestSymbol,
      worstSymbol,
      symbolCount: symbolStats.length,
    };
  }, [symbolStats]);

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || payload.length === 0) return null;

    const data = payload[0].payload as SymbolPerformance;

    return (
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3">
        <div className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
          {data.symbol}
        </div>
        <div className="space-y-1 text-sm">
          <div className="flex items-center justify-between gap-4">
            <span className="text-gray-600 dark:text-gray-400">P&L:</span>
            <span className={`font-semibold ${
              data.totalPnL >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
            }`}>
              ${data.totalPnL.toFixed(2)}
            </span>
          </div>
          <div className="flex items-center justify-between gap-4">
            <span className="text-gray-600 dark:text-gray-400">Win Rate:</span>
            <span className="font-semibold text-gray-900 dark:text-gray-100">
              {data.winRate.toFixed(1)}%
            </span>
          </div>
          <div className="flex items-center justify-between gap-4">
            <span className="text-gray-600 dark:text-gray-400">Trades:</span>
            <span className="font-semibold text-gray-900 dark:text-gray-100">
              {data.trades}
            </span>
          </div>
          <div className="flex items-center justify-between gap-4">
            <span className="text-gray-600 dark:text-gray-400">Profit Factor:</span>
            <span className="font-semibold text-blue-600 dark:text-blue-400">
              {data.profitFactor.toFixed(2)}
            </span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className={`bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Target className="w-5 h-5 text-blue-500" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Symbol Performance
            </h3>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Compare performance across {aggregateStats.symbolCount} symbols
          </p>
        </div>

        {/* View Toggle */}
        <div className="flex gap-2">
          <button
            onClick={() => setViewMode('chart')}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              viewMode === 'chart'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'
            }`}
          >
            Chart
          </button>
          <button
            onClick={() => setViewMode('table')}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              viewMode === 'table'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'
            }`}
          >
            Table
          </button>
        </div>
      </div>

      {/* Aggregate Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-4">
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Total Trades</div>
          <div className="text-lg font-bold text-gray-900 dark:text-gray-100">
            {aggregateStats.totalTrades}
          </div>
        </div>

        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Total P&L</div>
          <div className={`text-lg font-bold ${
            aggregateStats.totalPnL >= 0 
              ? 'text-green-600 dark:text-green-400' 
              : 'text-red-600 dark:text-red-400'
          }`}>
            ${aggregateStats.totalPnL.toFixed(2)}
          </div>
        </div>

        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Avg Win Rate</div>
          <div className="text-lg font-bold text-blue-600 dark:text-blue-400">
            {aggregateStats.avgWinRate.toFixed(1)}%
          </div>
        </div>

        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3">
          <div className="flex items-center gap-1 mb-1">
            <TrendingUp className="w-3 h-3 text-green-600 dark:text-green-400" />
            <span className="text-xs text-green-600 dark:text-green-400">Best Symbol</span>
          </div>
          <div className="text-sm font-bold text-green-600 dark:text-green-400">
            {aggregateStats.bestSymbol?.symbol || 'N/A'}
          </div>
          <div className="text-xs text-green-600 dark:text-green-400">
            ${aggregateStats.bestSymbol?.totalPnL.toFixed(2) || '0'}
          </div>
        </div>

        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
          <div className="flex items-center gap-1 mb-1">
            <TrendingDown className="w-3 h-3 text-red-600 dark:text-red-400" />
            <span className="text-xs text-red-600 dark:text-red-400">Worst Symbol</span>
          </div>
          <div className="text-sm font-bold text-red-600 dark:text-red-400">
            {aggregateStats.worstSymbol?.symbol || 'N/A'}
          </div>
          <div className="text-xs text-red-600 dark:text-red-400">
            ${aggregateStats.worstSymbol?.totalPnL.toFixed(2) || '0'}
          </div>
        </div>
      </div>

      {/* Chart View */}
      {viewMode === 'chart' && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <span className="text-sm text-gray-600 dark:text-gray-400">Sort by:</span>
            <select
              value={sortKey}
              onChange={(e) => setSortKey(e.target.value as SortKey)}
              className="px-3 py-1.5 bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="totalPnL">Total P&L</option>
              <option value="winRate">Win Rate</option>
              <option value="trades">Trade Count</option>
              <option value="profitFactor">Profit Factor</option>
              <option value="sharpeRatio">Sharpe Ratio</option>
              <option value="symbol">Symbol</option>
            </select>
            <button
              onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
              className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"
              title={sortOrder === 'asc' ? 'Ascending' : 'Descending'}
            >
              <ArrowUpDown className={`w-4 h-4 text-gray-600 dark:text-gray-400 ${
                sortOrder === 'desc' ? 'rotate-180' : ''
              } transition-transform`} />
            </button>
          </div>

          <ResponsiveContainer width="100%" height={height}>
            <BarChart data={sortedData} margin={{ top: 10, right: 30, left: 10, bottom: 60 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.1} />
              
              <XAxis
                dataKey="symbol"
                stroke="#6b7280"
                fontSize={12}
                tickLine={false}
                angle={-45}
                textAnchor="end"
                height={80}
              />
              
              <YAxis
                stroke="#6b7280"
                fontSize={12}
                tickLine={false}
                tickFormatter={(value) => `$${value.toFixed(0)}`}
              />
              
              <Tooltip content={<CustomTooltip />} />
              
              <Legend
                verticalAlign="top"
                height={36}
                iconType="square"
              />

              <Bar dataKey="totalPnL" name="Total P&L" radius={[4, 4, 0, 0]}>
                {sortedData.map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={entry.totalPnL >= 0 ? '#10b981' : '#ef4444'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Table View */}
      {viewMode === 'table' && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800">
              <tr>
                <th 
                  className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
                  onClick={() => handleSort('symbol')}
                >
                  <div className="flex items-center gap-1">
                    Symbol
                    {sortKey === 'symbol' && (
                      <ArrowUpDown className={`w-3 h-3 ${sortOrder === 'desc' ? 'rotate-180' : ''}`} />
                    )}
                  </div>
                </th>
                <th 
                  className="px-3 py-2 text-right text-xs font-medium text-gray-500 dark:text-gray-400 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
                  onClick={() => handleSort('trades')}
                >
                  <div className="flex items-center justify-end gap-1">
                    Trades
                    {sortKey === 'trades' && (
                      <ArrowUpDown className={`w-3 h-3 ${sortOrder === 'desc' ? 'rotate-180' : ''}`} />
                    )}
                  </div>
                </th>
                <th 
                  className="px-3 py-2 text-right text-xs font-medium text-gray-500 dark:text-gray-400 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
                  onClick={() => handleSort('winRate')}
                >
                  <div className="flex items-center justify-end gap-1">
                    Win Rate
                    {sortKey === 'winRate' && (
                      <ArrowUpDown className={`w-3 h-3 ${sortOrder === 'desc' ? 'rotate-180' : ''}`} />
                    )}
                  </div>
                </th>
                <th 
                  className="px-3 py-2 text-right text-xs font-medium text-gray-500 dark:text-gray-400 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
                  onClick={() => handleSort('totalPnL')}
                >
                  <div className="flex items-center justify-end gap-1">
                    Total P&L
                    {sortKey === 'totalPnL' && (
                      <ArrowUpDown className={`w-3 h-3 ${sortOrder === 'desc' ? 'rotate-180' : ''}`} />
                    )}
                  </div>
                </th>
                <th 
                  className="px-3 py-2 text-right text-xs font-medium text-gray-500 dark:text-gray-400 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
                  onClick={() => handleSort('profitFactor')}
                >
                  <div className="flex items-center justify-end gap-1">
                    Profit Factor
                    {sortKey === 'profitFactor' && (
                      <ArrowUpDown className={`w-3 h-3 ${sortOrder === 'desc' ? 'rotate-180' : ''}`} />
                    )}
                  </div>
                </th>
                <th 
                  className="px-3 py-2 text-right text-xs font-medium text-gray-500 dark:text-gray-400 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
                  onClick={() => handleSort('sharpeRatio')}
                >
                  <div className="flex items-center justify-end gap-1">
                    Sharpe
                    {sortKey === 'sharpeRatio' && (
                      <ArrowUpDown className={`w-3 h-3 ${sortOrder === 'desc' ? 'rotate-180' : ''}`} />
                    )}
                  </div>
                </th>
                <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 dark:text-gray-400">
                  Max DD
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {sortedData.map((symbol) => (
                <tr key={symbol.symbol} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                  <td className="px-3 py-2 font-semibold text-gray-900 dark:text-gray-100">
                    {symbol.symbol}
                  </td>
                  <td className="px-3 py-2 text-right text-gray-600 dark:text-gray-400">
                    {symbol.trades}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <span className={`font-semibold ${
                      symbol.winRate >= 50 
                        ? 'text-green-600 dark:text-green-400' 
                        : 'text-red-600 dark:text-red-400'
                    }`}>
                      {symbol.winRate.toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right">
                    <span className={`font-semibold ${
                      symbol.totalPnL >= 0 
                        ? 'text-green-600 dark:text-green-400' 
                        : 'text-red-600 dark:text-red-400'
                    }`}>
                      ${symbol.totalPnL.toFixed(2)}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right text-gray-900 dark:text-gray-100 font-semibold">
                    {symbol.profitFactor.toFixed(2)}
                  </td>
                  <td className="px-3 py-2 text-right text-gray-900 dark:text-gray-100 font-semibold">
                    {symbol.sharpeRatio.toFixed(2)}
                  </td>
                  <td className="px-3 py-2 text-right text-red-600 dark:text-red-400 font-semibold">
                    {symbol.maxDrawdown.toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

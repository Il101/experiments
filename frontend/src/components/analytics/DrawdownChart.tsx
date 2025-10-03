/**
 * DrawdownChart Component
 * Underwater equity curve showing drawdown depth over time
 */

import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceDot,
} from 'recharts';
import { AlertTriangle, TrendingDown, CheckCircle } from 'lucide-react';
import type { DrawdownPeriod, TimeSeriesPoint } from '../../types/analytics';

// ==================== Interfaces ====================

interface DrawdownChartProps {
  drawdownSeries: TimeSeriesPoint[];
  drawdownPeriods: DrawdownPeriod[];
  height?: number;
  className?: string;
}

interface ChartDataPoint {
  timestamp: string;
  drawdown: number;
  formattedDate: string;
  isPeak: boolean;
  isTrough: boolean;
}

// ==================== Component ====================

export const DrawdownChart: React.FC<DrawdownChartProps> = ({
  drawdownSeries,
  drawdownPeriods,
  height = 350,
  className = '',
}) => {
  // Transform data for chart
  const chartData: ChartDataPoint[] = React.useMemo(() => {
    const peakDates = new Set(drawdownPeriods.map(p => p.peakDate));
    const troughDates = new Set(drawdownPeriods.map(p => p.troughDate));

    return drawdownSeries.map(point => {
      const date = new Date(point.timestamp);
      const formattedDate = date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      });

      return {
        timestamp: point.timestamp,
        drawdown: point.value,
        formattedDate,
        isPeak: peakDates.has(point.timestamp),
        isTrough: troughDates.has(point.timestamp),
      };
    });
  }, [drawdownSeries, drawdownPeriods]);

  // Calculate stats
  const stats = React.useMemo(() => {
    const drawdowns = drawdownSeries.map(p => p.value);
    const maxDD = Math.min(...drawdowns);
    const currentDD = drawdowns[drawdowns.length - 1] || 0;
    const avgDD = drawdowns.filter(d => d < 0).length > 0
      ? drawdowns.filter(d => d < 0).reduce((sum, d) => sum + d, 0) / drawdowns.filter(d => d < 0).length
      : 0;

    const currentPeriod = drawdownPeriods.find(p => p.isCurrent);
    const maxPeriod = drawdownPeriods.reduce((max, p) => 
      Math.abs(p.drawdownPercent) > Math.abs(max.drawdownPercent) ? p : max
    , drawdownPeriods[0] || null);

    return {
      maxDD,
      currentDD,
      avgDD,
      currentPeriod,
      maxPeriod,
      totalPeriods: drawdownPeriods.length,
      recoveredPeriods: drawdownPeriods.filter(p => p.isRecovered).length,
    };
  }, [drawdownSeries, drawdownPeriods]);

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || payload.length === 0) return null;

    const data = payload[0].payload as ChartDataPoint;

    return (
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3">
        <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">
          {data.formattedDate}
        </div>
        <div className="space-y-1">
          <div className="flex items-center justify-between gap-4">
            <span className="text-sm text-gray-600 dark:text-gray-400">Drawdown:</span>
            <span className={`text-sm font-semibold ${
              data.drawdown < 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'
            }`}>
              {data.drawdown.toFixed(2)}%
            </span>
          </div>
          {data.isPeak && (
            <div className="text-xs text-blue-500 dark:text-blue-400">
              📈 Peak
            </div>
          )}
          {data.isTrough && (
            <div className="text-xs text-red-500 dark:text-red-400">
              📉 Trough
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className={`bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6 ${className}`}>
      {/* Header */}
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-1">
          <TrendingDown className="w-5 h-5 text-red-500" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Drawdown Analysis
          </h3>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Underwater equity curve (distance from peak)
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-3 border border-red-200 dark:border-red-800">
          <div className="text-xs text-red-600 dark:text-red-400 mb-1 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" />
            Max Drawdown
          </div>
          <div className="text-lg font-bold text-red-600 dark:text-red-400">
            {stats.maxDD.toFixed(2)}%
          </div>
        </div>

        <div className={`rounded-lg p-3 border ${
          stats.currentDD < 0 
            ? 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800' 
            : 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
        }`}>
          <div className={`text-xs mb-1 flex items-center gap-1 ${
            stats.currentDD < 0 
              ? 'text-orange-600 dark:text-orange-400' 
              : 'text-green-600 dark:text-green-400'
          }`}>
            {stats.currentDD < 0 ? (
              <TrendingDown className="w-3 h-3" />
            ) : (
              <CheckCircle className="w-3 h-3" />
            )}
            Current DD
          </div>
          <div className={`text-lg font-bold ${
            stats.currentDD < 0 
              ? 'text-orange-600 dark:text-orange-400' 
              : 'text-green-600 dark:text-green-400'
          }`}>
            {stats.currentDD.toFixed(2)}%
          </div>
        </div>

        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Average DD</div>
          <div className="text-lg font-bold text-gray-900 dark:text-gray-100">
            {stats.avgDD.toFixed(2)}%
          </div>
        </div>

        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Recovery Rate</div>
          <div className="text-lg font-bold text-blue-600 dark:text-blue-400">
            {stats.totalPeriods > 0 
              ? ((stats.recoveredPeriods / stats.totalPeriods) * 100).toFixed(0) 
              : 0}%
          </div>
        </div>
      </div>

      {/* Current Drawdown Info */}
      {stats.currentPeriod && (
        <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg p-4 mb-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-orange-500 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="font-semibold text-orange-900 dark:text-orange-100 mb-1">
                Currently in Drawdown
              </h4>
              <p className="text-sm text-orange-700 dark:text-orange-300">
                Down {Math.abs(stats.currentPeriod.drawdownPercent).toFixed(2)}% from peak 
                ({stats.currentPeriod.durationDays} days). 
                Peak was ${stats.currentPeriod.peakEquity.toFixed(2)}, 
                currently at ${stats.currentPeriod.currentEquity.toFixed(2)}.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Chart */}
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
          <defs>
            <linearGradient id="ddGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.6} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0.1} />
            </linearGradient>
          </defs>
          
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.1} />
          
          <XAxis
            dataKey="formattedDate"
            stroke="#6b7280"
            fontSize={12}
            tickLine={false}
          />
          
          <YAxis
            stroke="#6b7280"
            fontSize={12}
            tickLine={false}
            tickFormatter={(value) => `${value.toFixed(0)}%`}
            domain={['dataMin', 0]}
          />
          
          <Tooltip content={<CustomTooltip />} />
          
          {/* Zero line */}
          <ReferenceLine
            y={0}
            stroke="#10b981"
            strokeWidth={2}
            label={{ value: 'At Peak', position: 'right', fill: '#10b981', fontSize: 12 }}
          />

          {/* Max drawdown line */}
          <ReferenceLine
            y={stats.maxDD}
            stroke="#ef4444"
            strokeDasharray="3 3"
            label={{ value: `Max DD: ${stats.maxDD.toFixed(1)}%`, position: 'right', fill: '#ef4444', fontSize: 12 }}
          />

          {/* Area */}
          <Area
            type="monotone"
            dataKey="drawdown"
            stroke="#ef4444"
            strokeWidth={2}
            fill="url(#ddGradient)"
            name="Drawdown %"
          />

          {/* Peak markers */}
          {chartData
            .filter(d => d.isPeak)
            .map((point, index) => (
              <ReferenceDot
                key={`peak-${index}`}
                x={point.formattedDate}
                y={point.drawdown}
                r={4}
                fill="#3b82f6"
                stroke="#fff"
                strokeWidth={2}
              />
            ))}

          {/* Trough markers */}
          {chartData
            .filter(d => d.isTrough)
            .map((point, index) => (
              <ReferenceDot
                key={`trough-${index}`}
                x={point.formattedDate}
                y={point.drawdown}
                r={4}
                fill="#ef4444"
                stroke="#fff"
                strokeWidth={2}
              />
            ))}
        </AreaChart>
      </ResponsiveContainer>

      {/* Drawdown Periods Table */}
      {drawdownPeriods.length > 0 && (
        <div className="mt-6">
          <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
            Recent Drawdown Periods
          </h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400">
                    Period
                  </th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400">
                    Depth
                  </th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400">
                    Duration
                  </th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400">
                    Recovery
                  </th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {drawdownPeriods.slice(0, 5).map((period) => (
                  <tr key={period.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td className="px-3 py-2 text-gray-900 dark:text-gray-100">
                      {new Date(period.startDate).toLocaleDateString('en-US', { 
                        month: 'short', 
                        day: 'numeric' 
                      })}
                    </td>
                    <td className="px-3 py-2">
                      <span className="text-red-600 dark:text-red-400 font-semibold">
                        {period.drawdownPercent.toFixed(2)}%
                      </span>
                    </td>
                    <td className="px-3 py-2 text-gray-600 dark:text-gray-400">
                      {period.durationDays}d
                    </td>
                    <td className="px-3 py-2 text-gray-600 dark:text-gray-400">
                      {period.recoveryDays ? `${period.recoveryDays}d` : '-'}
                    </td>
                    <td className="px-3 py-2">
                      {period.isRecovered ? (
                        <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded text-xs font-medium">
                          <CheckCircle className="w-3 h-3" />
                          Recovered
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-1 bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 rounded text-xs font-medium">
                          <AlertTriangle className="w-3 h-3" />
                          Ongoing
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

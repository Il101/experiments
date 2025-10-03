/**
 * EquityCurveChart Component
 * Interactive line chart showing cumulative P&L over time with drawdown overlay
 */

import React, { useState } from 'react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  Brush,
} from 'recharts';
import { TrendingUp, TrendingDown, Maximize2, Minimize2 } from 'lucide-react';
import type { TimeSeriesPoint } from '../../types/analytics';

// ==================== Interfaces ====================

interface EquityCurveChartProps {
  data: TimeSeriesPoint[];
  startingEquity: number;
  showDrawdown?: boolean;
  showBrush?: boolean;
  height?: number;
  className?: string;
}

interface ChartDataPoint {
  timestamp: string;
  date: string;
  equity: number;
  drawdown: number;
  formattedDate: string;
}

// ==================== Component ====================

export const EquityCurveChart: React.FC<EquityCurveChartProps> = ({
  data,
  startingEquity,
  showDrawdown = true,
  showBrush = true,
  height = 400,
  className = '',
}) => {
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Transform data for chart
  const chartData: ChartDataPoint[] = React.useMemo(() => {
    let peak = startingEquity;
    
    return data.map(point => {
      const equity = point.value;
      
      // Update peak
      if (equity > peak) {
        peak = equity;
      }
      
      // Calculate drawdown
      const drawdown = peak > 0 ? ((equity - peak) / peak) * 100 : 0;
      
      // Format date
      const date = new Date(point.timestamp);
      const formattedDate = date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });

      return {
        timestamp: point.timestamp,
        date: date.toISOString(),
        equity,
        drawdown,
        formattedDate,
      };
    });
  }, [data, startingEquity]);

  // Calculate stats
  const stats = React.useMemo(() => {
    if (chartData.length === 0) {
      return {
        currentEquity: startingEquity,
        totalReturn: 0,
        totalReturnPercent: 0,
        peakEquity: startingEquity,
        currentDrawdown: 0,
      };
    }

    const currentEquity = chartData[chartData.length - 1].equity;
    const totalReturn = currentEquity - startingEquity;
    const totalReturnPercent = ((currentEquity - startingEquity) / startingEquity) * 100;
    const peakEquity = Math.max(...chartData.map(d => d.equity));
    const currentDrawdown = chartData[chartData.length - 1].drawdown;

    return {
      currentEquity,
      totalReturn,
      totalReturnPercent,
      peakEquity,
      currentDrawdown,
    };
  }, [chartData, startingEquity]);

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
            <span className="text-sm text-gray-600 dark:text-gray-400">Equity:</span>
            <span className="text-sm font-semibold text-blue-600 dark:text-blue-400">
              ${data.equity.toFixed(2)}
            </span>
          </div>
          {showDrawdown && (
            <div className="flex items-center justify-between gap-4">
              <span className="text-sm text-gray-600 dark:text-gray-400">Drawdown:</span>
              <span className={`text-sm font-semibold ${
                data.drawdown < 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'
              }`}>
                {data.drawdown.toFixed(2)}%
              </span>
            </div>
          )}
          <div className="flex items-center justify-between gap-4">
            <span className="text-sm text-gray-600 dark:text-gray-400">Return:</span>
            <span className={`text-sm font-semibold ${
              data.equity >= startingEquity 
                ? 'text-green-600 dark:text-green-400' 
                : 'text-red-600 dark:text-red-400'
            }`}>
              ${(data.equity - startingEquity).toFixed(2)} 
              ({((data.equity - startingEquity) / startingEquity * 100).toFixed(2)}%)
            </span>
          </div>
        </div>
      </div>
    );
  };

  const chartHeight = isFullscreen ? 600 : height;

  return (
    <div className={`bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
            Equity Curve
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Cumulative P&L over time
          </p>
        </div>
        <button
          onClick={() => setIsFullscreen(!isFullscreen)}
          className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          title={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
        >
          {isFullscreen ? (
            <Minimize2 className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          ) : (
            <Maximize2 className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          )}
        </button>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-4">
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Current Equity</div>
          <div className="text-lg font-bold text-gray-900 dark:text-gray-100">
            ${stats.currentEquity.toFixed(2)}
          </div>
        </div>
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Total Return</div>
          <div className={`text-lg font-bold ${
            stats.totalReturn >= 0 
              ? 'text-green-600 dark:text-green-400' 
              : 'text-red-600 dark:text-red-400'
          }`}>
            {stats.totalReturn >= 0 ? '+' : ''}${stats.totalReturn.toFixed(2)}
          </div>
        </div>
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Return %</div>
          <div className={`text-lg font-bold flex items-center gap-1 ${
            stats.totalReturnPercent >= 0 
              ? 'text-green-600 dark:text-green-400' 
              : 'text-red-600 dark:text-red-400'
          }`}>
            {stats.totalReturnPercent >= 0 ? (
              <TrendingUp className="w-4 h-4" />
            ) : (
              <TrendingDown className="w-4 h-4" />
            )}
            {stats.totalReturnPercent >= 0 ? '+' : ''}{stats.totalReturnPercent.toFixed(2)}%
          </div>
        </div>
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Peak Equity</div>
          <div className="text-lg font-bold text-blue-600 dark:text-blue-400">
            ${stats.peakEquity.toFixed(2)}
          </div>
        </div>
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Current DD</div>
          <div className={`text-lg font-bold ${
            stats.currentDrawdown < 0 
              ? 'text-red-600 dark:text-red-400' 
              : 'text-green-600 dark:text-green-400'
          }`}>
            {stats.currentDrawdown.toFixed(2)}%
          </div>
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={chartHeight}>
        <LineChart data={chartData} margin={{ top: 10, right: 30, left: 10, bottom: showBrush ? 50 : 10 }}>
          <defs>
            <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
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
            tickFormatter={(value) => `$${value.toFixed(0)}`}
          />
          
          <Tooltip content={<CustomTooltip />} />
          
          <Legend
            verticalAlign="top"
            height={36}
            iconType="line"
            wrapperStyle={{ paddingBottom: '10px' }}
          />

          {/* Starting equity reference line */}
          <ReferenceLine
            y={startingEquity}
            stroke="#6b7280"
            strokeDasharray="3 3"
            label={{ value: 'Start', position: 'right', fill: '#6b7280', fontSize: 12 }}
          />

          {/* Peak equity reference line */}
          <ReferenceLine
            y={stats.peakEquity}
            stroke="#3b82f6"
            strokeDasharray="3 3"
            label={{ value: 'Peak', position: 'right', fill: '#3b82f6', fontSize: 12 }}
          />

          {/* Equity curve */}
          <Line
            type="monotone"
            dataKey="equity"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={false}
            name="Equity"
            animationDuration={1000}
          />

          {/* Brush for zooming */}
          {showBrush && chartData.length > 20 && (
            <Brush
              dataKey="formattedDate"
              height={30}
              stroke="#3b82f6"
              fill="#1f2937"
            />
          )}
        </LineChart>
      </ResponsiveContainer>

      {/* Drawdown Area Chart (if enabled) */}
      {showDrawdown && (
        <div className="mt-6">
          <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
            Drawdown Overlay
          </h4>
          <ResponsiveContainer width="100%" height={150}>
            <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
              <defs>
                <linearGradient id="drawdownGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.5} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
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
              />
              
              <Tooltip content={<CustomTooltip />} />
              
              <ReferenceLine y={0} stroke="#6b7280" />
              
              <Area
                type="monotone"
                dataKey="drawdown"
                stroke="#ef4444"
                fill="url(#drawdownGradient)"
                name="Drawdown %"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};

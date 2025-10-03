/**
 * MetricsOverview Component
 * Grid of key performance metrics with color-coded indicators
 */

import React from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  Award,
  AlertTriangle,
  Target,
  Activity,
  BarChart3,
  DollarSign,
  Clock,
} from 'lucide-react';
import type { PerformanceMetrics } from '../../types/analytics';

// ==================== Interfaces ====================

interface MetricsOverviewProps {
  metrics: PerformanceMetrics;
  previousMetrics?: PerformanceMetrics;
  className?: string;
}

interface MetricCardProps {
  label: string;
  value: number | string;
  format: 'number' | 'percent' | 'currency' | 'ratio' | 'grade' | 'days';
  decimals?: number;
  icon?: React.ReactNode;
  change?: number;
  changePercent?: number;
  status?: 'good' | 'warning' | 'bad' | 'neutral';
  tooltip?: string;
  benchmark?: number;
}

// ==================== Component ====================

export const MetricsOverview: React.FC<MetricsOverviewProps> = ({
  metrics,
  previousMetrics,
  className = '',
}) => {
  // Calculate changes if previous metrics available
  const getChange = (current: number, previous?: number) => {
    if (!previous) return undefined;
    return current - previous;
  };

  const getChangePercent = (current: number, previous?: number) => {
    if (!previous || previous === 0) return undefined;
    return ((current - previous) / Math.abs(previous)) * 100;
  };

  // Determine status based on value and direction
  const getStatus = (
    change: number | undefined,
    goodDirection: 'higher' | 'lower'
  ): MetricCardProps['status'] => {
    if (change === undefined) return 'neutral';
    
    const isPositiveChange = change > 0;
    const isGoodChange = goodDirection === 'higher' ? isPositiveChange : !isPositiveChange;
    
    if (Math.abs(change) < 0.01) return 'neutral';
    return isGoodChange ? 'good' : 'bad';
  };

  // Key metrics to display
  const keyMetrics: MetricCardProps[] = [
    {
      label: 'Total P&L',
      value: metrics.totalPnL,
      format: 'currency',
      decimals: 2,
      icon: <DollarSign className="w-5 h-5" />,
      change: getChange(metrics.totalPnL, previousMetrics?.totalPnL),
      changePercent: getChangePercent(metrics.totalPnL, previousMetrics?.totalPnL),
      status: getStatus(getChange(metrics.totalPnL, previousMetrics?.totalPnL), 'higher'),
      tooltip: 'Total profit/loss including open positions',
    },
    {
      label: 'Win Rate',
      value: metrics.winRate,
      format: 'percent',
      decimals: 1,
      icon: <Target className="w-5 h-5" />,
      change: getChange(metrics.winRate, previousMetrics?.winRate),
      changePercent: getChangePercent(metrics.winRate, previousMetrics?.winRate),
      status: getStatus(getChange(metrics.winRate, previousMetrics?.winRate), 'higher'),
      tooltip: 'Percentage of winning trades',
      benchmark: 50,
    },
    {
      label: 'Profit Factor',
      value: metrics.profitFactor,
      format: 'ratio',
      decimals: 2,
      icon: <BarChart3 className="w-5 h-5" />,
      change: getChange(metrics.profitFactor, previousMetrics?.profitFactor),
      changePercent: getChangePercent(metrics.profitFactor, previousMetrics?.profitFactor),
      status: getStatus(getChange(metrics.profitFactor, previousMetrics?.profitFactor), 'higher'),
      tooltip: 'Gross profit / Gross loss (>1 is profitable)',
      benchmark: 1.5,
    },
    {
      label: 'Sharpe Ratio',
      value: metrics.sharpeRatio,
      format: 'ratio',
      decimals: 2,
      icon: <Activity className="w-5 h-5" />,
      change: getChange(metrics.sharpeRatio, previousMetrics?.sharpeRatio),
      changePercent: getChangePercent(metrics.sharpeRatio, previousMetrics?.sharpeRatio),
      status: getStatus(getChange(metrics.sharpeRatio, previousMetrics?.sharpeRatio), 'higher'),
      tooltip: 'Risk-adjusted return (>1 is good)',
      benchmark: 1.0,
    },
    {
      label: 'Max Drawdown',
      value: metrics.maxDrawdown,
      format: 'percent',
      decimals: 1,
      icon: <AlertTriangle className="w-5 h-5" />,
      change: getChange(metrics.maxDrawdown, previousMetrics?.maxDrawdown),
      changePercent: getChangePercent(metrics.maxDrawdown, previousMetrics?.maxDrawdown),
      status: getStatus(getChange(metrics.maxDrawdown, previousMetrics?.maxDrawdown), 'lower'),
      tooltip: 'Largest peak-to-trough decline',
    },
    {
      label: 'Expectancy',
      value: metrics.expectancy,
      format: 'currency',
      decimals: 2,
      icon: <DollarSign className="w-5 h-5" />,
      change: getChange(metrics.expectancy, previousMetrics?.expectancy),
      changePercent: getChangePercent(metrics.expectancy, previousMetrics?.expectancy),
      status: getStatus(getChange(metrics.expectancy, previousMetrics?.expectancy), 'higher'),
      tooltip: 'Expected value per trade',
    },
    {
      label: 'Total Trades',
      value: metrics.totalTrades,
      format: 'number',
      decimals: 0,
      icon: <BarChart3 className="w-5 h-5" />,
      tooltip: 'Total number of closed trades',
    },
    {
      label: 'Avg Trade',
      value: metrics.averageTrade,
      format: 'currency',
      decimals: 2,
      icon: <DollarSign className="w-5 h-5" />,
      tooltip: 'Average profit/loss per trade',
    },
    {
      label: 'Performance Grade',
      value: metrics.overallGrade,
      format: 'grade',
      icon: <Award className="w-5 h-5" />,
      tooltip: `Overall performance score: ${metrics.gradeScore}/100`,
    },
    {
      label: 'Avg Duration',
      value: metrics.averageTradeDuration,
      format: 'days',
      decimals: 1,
      icon: <Clock className="w-5 h-5" />,
      tooltip: 'Average trade duration in hours',
    },
    {
      label: 'Current Streak',
      value: metrics.currentStreak,
      format: 'number',
      decimals: 0,
      icon: metrics.currentStreak > 0 ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />,
      status: metrics.currentStreak > 0 ? 'good' : metrics.currentStreak < 0 ? 'bad' : 'neutral',
      tooltip: `Current ${metrics.currentStreak > 0 ? 'winning' : 'losing'} streak`,
    },
    {
      label: 'Recovery Factor',
      value: metrics.recoveryFactor,
      format: 'ratio',
      decimals: 2,
      icon: <Activity className="w-5 h-5" />,
      tooltip: 'Net profit / Max drawdown',
    },
  ];

  return (
    <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 ${className}`}>
      {keyMetrics.map((metric, index) => (
        <MetricCard key={index} {...metric} />
      ))}
    </div>
  );
};

// ==================== MetricCard Component ====================

const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  format,
  decimals = 2,
  icon,
  change,
  changePercent,
  status = 'neutral',
  tooltip,
  benchmark,
}) => {
  // Format value based on type
  const formatValue = (val: number | string): string => {
    if (typeof val === 'string') return val;

    switch (format) {
      case 'currency':
        return `$${val.toFixed(decimals)}`;
      case 'percent':
        return `${val.toFixed(decimals)}%`;
      case 'ratio':
        return val.toFixed(decimals);
      case 'days':
        return `${val.toFixed(decimals)}h`;
      case 'number':
        return val.toFixed(decimals);
      case 'grade':
        return val.toString();
      default:
        return val.toString();
    }
  };

  // Status colors
  const getStatusColor = () => {
    switch (status) {
      case 'good':
        return 'border-green-500 bg-green-50 dark:bg-green-900/20';
      case 'warning':
        return 'border-yellow-500 bg-yellow-50 dark:bg-yellow-900/20';
      case 'bad':
        return 'border-red-500 bg-red-50 dark:bg-red-900/20';
      default:
        return 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900';
    }
  };

  const getValueColor = () => {
    switch (status) {
      case 'good':
        return 'text-green-600 dark:text-green-400';
      case 'warning':
        return 'text-yellow-600 dark:text-yellow-400';
      case 'bad':
        return 'text-red-600 dark:text-red-400';
      default:
        return 'text-gray-900 dark:text-gray-100';
    }
  };

  const getChangeColor = () => {
    if (!change) return 'text-gray-500';
    return change > 0 
      ? 'text-green-600 dark:text-green-400' 
      : 'text-red-600 dark:text-red-400';
  };

  // Compare with benchmark
  const isBelowBenchmark = benchmark !== undefined && typeof value === 'number' && value < benchmark;

  return (
    <div
      className={`relative rounded-lg border-2 p-4 transition-all hover:shadow-md ${getStatusColor()}`}
      title={tooltip}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
          {label}
        </span>
        {icon && (
          <div className={`${getValueColor()}`}>
            {icon}
          </div>
        )}
      </div>

      {/* Value */}
      <div className={`text-2xl font-bold ${getValueColor()} mb-1`}>
        {formatValue(value)}
      </div>

      {/* Change & Benchmark */}
      <div className="flex items-center justify-between text-xs">
        {/* Change */}
        {change !== undefined && changePercent !== undefined && (
          <div className={`flex items-center gap-1 ${getChangeColor()}`}>
            {change > 0 ? (
              <TrendingUp className="w-3 h-3" />
            ) : change < 0 ? (
              <TrendingDown className="w-3 h-3" />
            ) : null}
            <span>
              {change > 0 ? '+' : ''}{formatValue(change)}
              {' '}({changePercent > 0 ? '+' : ''}{changePercent.toFixed(1)}%)
            </span>
          </div>
        )}

        {/* Benchmark */}
        {benchmark !== undefined && (
          <div className={`text-xs ${isBelowBenchmark ? 'text-red-500' : 'text-gray-500'}`}>
            Target: {formatValue(benchmark)}
          </div>
        )}
      </div>

      {/* Benchmark warning indicator */}
      {isBelowBenchmark && (
        <div className="absolute top-2 right-2">
          <AlertTriangle className="w-4 h-4 text-red-500" />
        </div>
      )}
    </div>
  );
};

// ==================== Summary Card ====================

export const PerformanceSummaryCard: React.FC<{
  metrics: PerformanceMetrics;
  className?: string;
}> = ({ metrics, className = '' }) => {
  // Determine overall status
  const getOverallStatus = (): 'excellent' | 'good' | 'average' | 'poor' => {
    const score = metrics.gradeScore;
    if (score >= 85) return 'excellent';
    if (score >= 70) return 'good';
    if (score >= 55) return 'average';
    return 'poor';
  };

  const status = getOverallStatus();

  const statusConfig = {
    excellent: {
      color: 'bg-green-500',
      textColor: 'text-green-600 dark:text-green-400',
      bgColor: 'bg-green-50 dark:bg-green-900/20',
      borderColor: 'border-green-500',
      label: 'Excellent',
      icon: '🎉',
    },
    good: {
      color: 'bg-blue-500',
      textColor: 'text-blue-600 dark:text-blue-400',
      bgColor: 'bg-blue-50 dark:bg-blue-900/20',
      borderColor: 'border-blue-500',
      label: 'Good',
      icon: '👍',
    },
    average: {
      color: 'bg-yellow-500',
      textColor: 'text-yellow-600 dark:text-yellow-400',
      bgColor: 'bg-yellow-50 dark:bg-yellow-900/20',
      borderColor: 'border-yellow-500',
      label: 'Average',
      icon: '⚠️',
    },
    poor: {
      color: 'bg-red-500',
      textColor: 'text-red-600 dark:text-red-400',
      bgColor: 'bg-red-50 dark:bg-red-900/20',
      borderColor: 'border-red-500',
      label: 'Needs Improvement',
      icon: '📉',
    },
  };

  const config = statusConfig[status];

  // Key highlights
  const highlights = [
    {
      label: 'Best',
      value: `${metrics.largestWin.toFixed(2)} (${((metrics.largestWin / metrics.averageWin) || 0).toFixed(1)}× avg)`,
      icon: '🏆',
    },
    {
      label: 'Worst',
      value: `${metrics.largestLoss.toFixed(2)} (${((Math.abs(metrics.largestLoss) / Math.abs(metrics.averageLoss)) || 0).toFixed(1)}× avg)`,
      icon: '💔',
    },
    {
      label: 'Win Streak',
      value: `${metrics.longestWinStreak} trades`,
      icon: '🔥',
    },
    {
      label: 'Trading Days',
      value: `${metrics.tradingDays} days`,
      icon: '📅',
    },
  ];

  return (
    <div className={`${config.bgColor} border-2 ${config.borderColor} rounded-lg p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`w-12 h-12 ${config.color} rounded-lg flex items-center justify-center text-2xl`}>
            {config.icon}
          </div>
          <div>
            <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">
              Performance Summary
            </h3>
            <p className={`text-sm ${config.textColor} font-semibold`}>
              {config.label} - Grade {metrics.overallGrade}
            </p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold text-gray-900 dark:text-gray-100">
            {metrics.gradeScore}
          </div>
          <div className="text-sm text-gray-500">/ 100</div>
        </div>
      </div>

      {/* Score Bar */}
      <div className="mb-4">
        <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div
            className={`h-full ${config.color} transition-all duration-500`}
            style={{ width: `${metrics.gradeScore}%` }}
          />
        </div>
      </div>

      {/* Highlights */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {highlights.map((highlight, index) => (
          <div key={index} className="bg-white dark:bg-gray-800 rounded-lg p-3">
            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
              {highlight.icon} {highlight.label}
            </div>
            <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              {highlight.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

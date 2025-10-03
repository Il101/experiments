/**
 * PerformanceHeatmap Component
 * Calendar heatmap showing daily returns with color intensity
 */

import React from 'react';
import { Calendar, TrendingUp, TrendingDown } from 'lucide-react';

// ==================== Interfaces ====================

interface PerformanceHeatmapProps {
  dailyReturns: Array<{
    date: string;
    return: number;
    trades: number;
  }>;
  className?: string;
}

interface DayCell {
  date: Date;
  dateStr: string;
  return: number;
  trades: number;
  intensity: number; // 0-1
  isEmpty: boolean;
}

interface WeekRow {
  weekNumber: number;
  days: (DayCell | null)[];
}

// ==================== Component ====================

export const PerformanceHeatmap: React.FC<PerformanceHeatmapProps> = ({
  dailyReturns,
  className = '',
}) => {
  // Calculate date range (last 3 months)
  const { weeks, stats } = React.useMemo(() => {
    const today = new Date();
    const threeMonthsAgo = new Date(today);
    threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3);

    // Create a map of daily returns
    const returnsMap = new Map(
      dailyReturns.map(d => [d.date, d])
    );

    // Calculate stats
    const returns = dailyReturns.map(d => d.return);
    const maxReturn = returns.length > 0 ? Math.max(...returns) : 0;
    const minReturn = returns.length > 0 ? Math.min(...returns) : 0;
    const absMax = Math.max(Math.abs(maxReturn), Math.abs(minReturn));

    const positiveReturns = returns.filter(r => r > 0);
    const negativeReturns = returns.filter(r => r < 0);
    const avgPositive = positiveReturns.length > 0
      ? positiveReturns.reduce((sum, r) => sum + r, 0) / positiveReturns.length
      : 0;
    const avgNegative = negativeReturns.length > 0
      ? negativeReturns.reduce((sum, r) => sum + r, 0) / negativeReturns.length
      : 0;

    // Build calendar grid (Sunday = 0, Saturday = 6)
    const weeksArray: WeekRow[] = [];
    let currentDate = new Date(threeMonthsAgo);
    
    // Start from the first Sunday before the start date
    const dayOfWeek = currentDate.getDay();
    if (dayOfWeek !== 0) {
      currentDate.setDate(currentDate.getDate() - dayOfWeek);
    }

    let weekNumber = 0;
    while (currentDate <= today) {
      const weekDays: (DayCell | null)[] = [];
      
      for (let i = 0; i < 7; i++) {
        const dateStr = currentDate.toISOString().split('T')[0];
        const dayData = returnsMap.get(dateStr);
        
        if (currentDate >= threeMonthsAgo && currentDate <= today) {
          const intensity = dayData && absMax > 0 
            ? Math.abs(dayData.return) / absMax 
            : 0;
          
          weekDays.push({
            date: new Date(currentDate),
            dateStr,
            return: dayData?.return || 0,
            trades: dayData?.trades || 0,
            intensity,
            isEmpty: !dayData,
          });
        } else {
          weekDays.push(null);
        }
        
        currentDate.setDate(currentDate.getDate() + 1);
      }
      
      weeksArray.push({
        weekNumber: weekNumber++,
        days: weekDays,
      });
    }

    return {
      weeks: weeksArray,
      stats: {
        maxReturn,
        minReturn,
        avgPositive,
        avgNegative,
        positiveDays: positiveReturns.length,
        negativeDays: negativeReturns.length,
        totalDays: dailyReturns.length,
      },
    };
  }, [dailyReturns]);

  // Get cell color based on return
  const getCellColor = (cell: DayCell): string => {
    if (cell.isEmpty) {
      return 'bg-gray-100 dark:bg-gray-800';
    }

    if (cell.return === 0) {
      return 'bg-gray-200 dark:bg-gray-700';
    }

    if (cell.return > 0) {
      // Green scale (lighter to darker based on intensity)
      return `bg-green-500`;
    } else {
      // Red scale (lighter to darker based on intensity)
      return `bg-red-500`;
    }
  };

  const getCellOpacity = (cell: DayCell): number => {
    if (cell.isEmpty || cell.return === 0) return 1;
    return 0.3 + (cell.intensity * 0.7);
  };

  const [hoveredCell, setHoveredCell] = React.useState<DayCell | null>(null);

  const dayLabels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  return (
    <div className={`bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6 ${className}`}>
      {/* Header */}
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-1">
          <Calendar className="w-5 h-5 text-purple-500" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Performance Calendar
          </h3>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Daily returns heatmap (last 3 months)
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3 border border-green-200 dark:border-green-800">
          <div className="flex items-center gap-1 mb-1">
            <TrendingUp className="w-4 h-4 text-green-600 dark:text-green-400" />
            <span className="text-xs text-green-600 dark:text-green-400">Positive Days</span>
          </div>
          <div className="text-lg font-bold text-green-600 dark:text-green-400">
            {stats.positiveDays}
          </div>
          <div className="text-xs text-green-600 dark:text-green-400">
            Avg: {stats.avgPositive.toFixed(2)}%
          </div>
        </div>

        <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-3 border border-red-200 dark:border-red-800">
          <div className="flex items-center gap-1 mb-1">
            <TrendingDown className="w-4 h-4 text-red-600 dark:text-red-400" />
            <span className="text-xs text-red-600 dark:text-red-400">Negative Days</span>
          </div>
          <div className="text-lg font-bold text-red-600 dark:text-red-400">
            {stats.negativeDays}
          </div>
          <div className="text-xs text-red-600 dark:text-red-400">
            Avg: {stats.avgNegative.toFixed(2)}%
          </div>
        </div>

        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Best Day</div>
          <div className="text-lg font-bold text-green-600 dark:text-green-400">
            +{stats.maxReturn.toFixed(2)}%
          </div>
        </div>

        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Worst Day</div>
          <div className="text-lg font-bold text-red-600 dark:text-red-400">
            {stats.minReturn.toFixed(2)}%
          </div>
        </div>
      </div>

      {/* Calendar Grid */}
      <div className="overflow-x-auto">
        <div className="inline-block min-w-full">
          {/* Day labels */}
          <div className="flex gap-1 mb-2">
            <div className="w-8" /> {/* Spacer for week numbers */}
            {dayLabels.map((day, index) => (
              <div
                key={index}
                className="w-8 h-8 flex items-center justify-center text-xs font-medium text-gray-500 dark:text-gray-400"
              >
                {day[0]}
              </div>
            ))}
          </div>

          {/* Calendar rows */}
          {weeks.map((week) => (
            <div key={week.weekNumber} className="flex gap-1 mb-1">
              {/* Week number */}
              <div className="w-8 h-8 flex items-center justify-center text-xs text-gray-400">
                {week.weekNumber + 1}
              </div>

              {/* Day cells */}
              {week.days.map((cell, dayIndex) => (
                <div
                  key={dayIndex}
                  className={`w-8 h-8 rounded ${
                    cell ? getCellColor(cell) : 'bg-transparent'
                  } cursor-pointer transition-all hover:ring-2 hover:ring-blue-500`}
                  style={cell ? { opacity: getCellOpacity(cell) } : undefined}
                  onMouseEnter={() => cell && setHoveredCell(cell)}
                  onMouseLeave={() => setHoveredCell(null)}
                  title={cell ? `${cell.dateStr}: ${cell.return.toFixed(2)}% (${cell.trades} trades)` : undefined}
                />
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="mt-4 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
          <span>Less</span>
          <div className="flex gap-1">
            {[0.2, 0.4, 0.6, 0.8, 1.0].map((opacity, index) => (
              <div
                key={index}
                className="w-4 h-4 rounded bg-green-500"
                style={{ opacity }}
              />
            ))}
          </div>
          <span>More (Profit)</span>
          <div className="mx-2">|</div>
          <div className="flex gap-1">
            {[0.2, 0.4, 0.6, 0.8, 1.0].map((opacity, index) => (
              <div
                key={index}
                className="w-4 h-4 rounded bg-red-500"
                style={{ opacity }}
              />
            ))}
          </div>
          <span>More (Loss)</span>
        </div>

        {/* Hover info */}
        {hoveredCell && (
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
            {new Date(hoveredCell.dateStr).toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric',
              year: 'numeric',
            })}
            : <span className={hoveredCell.return >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}>
              {hoveredCell.return >= 0 ? '+' : ''}{hoveredCell.return.toFixed(2)}%
            </span>
            {' '}({hoveredCell.trades} {hoveredCell.trades === 1 ? 'trade' : 'trades'})
          </div>
        )}
      </div>

      {/* Win rate by day of week */}
      <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
        <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
          Performance by Day of Week
        </h4>
        <div className="grid grid-cols-7 gap-2">
          {dayLabels.map((day, index) => {
            const dayReturns = dailyReturns.filter(d => {
              const date = new Date(d.date);
              return date.getDay() === index;
            });

            const avgReturn = dayReturns.length > 0
              ? dayReturns.reduce((sum, d) => sum + d.return, 0) / dayReturns.length
              : 0;

            return (
              <div key={index} className="text-center">
                <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                  {day}
                </div>
                <div className={`text-sm font-bold ${
                  avgReturn >= 0 
                    ? 'text-green-600 dark:text-green-400' 
                    : 'text-red-600 dark:text-red-400'
                }`}>
                  {avgReturn >= 0 ? '+' : ''}{avgReturn.toFixed(2)}%
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

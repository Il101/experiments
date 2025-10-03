/**
 * Drawdown Analyzer
 * Identifies and analyzes all drawdown periods in trading history
 */

import type { 
  DrawdownPeriod, 
  DrawdownAnalysis, 
  TimeSeriesPoint 
} from '../types/analytics';

// ==================== Interfaces ====================

interface EquityPoint {
  timestamp: string;
  date: Date;
  equity: number;
  pnl: number;
  tradeId?: string;
}

// ==================== Drawdown Analyzer ====================

export class DrawdownAnalyzer {
  private equityCurve: EquityPoint[];
  private startingEquity: number;

  constructor(equityCurve: EquityPoint[], startingEquity: number = 10000) {
    this.equityCurve = equityCurve.sort(
      (a, b) => a.date.getTime() - b.date.getTime()
    );
    this.startingEquity = startingEquity;
  }

  /**
   * Analyze all drawdown periods
   */
  public analyzeDrawdowns(): DrawdownAnalysis {
    const periods = this.findDrawdownPeriods();
    
    const currentDrawdown = periods.find(p => p.isCurrent) || null;
    const maxDrawdown = this.findMaxDrawdown(periods);
    const longestDrawdown = this.findLongestDrawdown(periods);
    
    const recoveredPeriods = periods.filter(p => p.isRecovered);
    const averageDrawdownPercent = recoveredPeriods.length > 0
      ? recoveredPeriods.reduce((sum, p) => sum + Math.abs(p.drawdownPercent), 0) / recoveredPeriods.length
      : 0;
    
    const averageDrawdownDuration = recoveredPeriods.length > 0
      ? recoveredPeriods.reduce((sum, p) => sum + p.durationDays, 0) / recoveredPeriods.length
      : 0;
    
    const averageRecoveryTime = recoveredPeriods.filter(p => p.recoveryDays !== null).length > 0
      ? recoveredPeriods
          .filter(p => p.recoveryDays !== null)
          .reduce((sum, p) => sum + p.recoveryDays!, 0) / 
        recoveredPeriods.filter(p => p.recoveryDays !== null).length
      : 0;
    
    const drawdownSeries = this.buildDrawdownSeries();
    
    return {
      periods,
      currentDrawdown,
      maxDrawdown,
      longestDrawdown,
      averageDrawdownPercent,
      averageDrawdownDuration,
      averageRecoveryTime,
      totalDrawdowns: periods.length,
      recoveredDrawdowns: recoveredPeriods.length,
      ongoingDrawdowns: periods.filter(p => !p.isRecovered).length,
      drawdownSeries,
    };
  }

  /**
   * Find all drawdown periods in equity curve
   */
  private findDrawdownPeriods(): DrawdownPeriod[] {
    const periods: DrawdownPeriod[] = [];
    let peak = this.startingEquity;
    let peakDate: Date | null = null;
    let peakIndex = 0;
    let inDrawdown = false;
    let drawdownStart: Date | null = null;
    let troughEquity = peak;
    let troughDate: Date | null = null;
    let troughIndex = 0;
    let drawdownId = 0;

    this.equityCurve.forEach((point, index) => {
      const { date, equity } = point;

      if (equity >= peak) {
        // New peak reached
        if (inDrawdown && drawdownStart && troughDate && peakDate) {
          // Drawdown recovered
          const period = this.createDrawdownPeriod({
            id: `dd-${++drawdownId}`,
            startDate: drawdownStart,
            peakDate,
            troughDate,
            endDate: date,
            peakEquity: peak,
            troughEquity,
            currentEquity: equity,
            peakIndex,
            troughIndex,
            endIndex: index,
            isRecovered: true,
            isCurrent: false,
          });
          periods.push(period);
        }

        peak = equity;
        peakDate = date;
        peakIndex = index;
        inDrawdown = false;
        drawdownStart = null;
      } else {
        // In drawdown
        if (!inDrawdown) {
          inDrawdown = true;
          drawdownStart = date;
          troughEquity = equity;
          troughDate = date;
          troughIndex = index;
        }

        if (equity < troughEquity) {
          troughEquity = equity;
          troughDate = date;
          troughIndex = index;
        }
      }
    });

    // Handle ongoing drawdown
    if (inDrawdown && drawdownStart && troughDate && peakDate) {
      const currentEquity = this.equityCurve[this.equityCurve.length - 1].equity;
      const period = this.createDrawdownPeriod({
        id: `dd-${++drawdownId}`,
        startDate: drawdownStart,
        peakDate,
        troughDate,
        endDate: null,
        peakEquity: peak,
        troughEquity,
        currentEquity,
        peakIndex,
        troughIndex,
        endIndex: this.equityCurve.length - 1,
        isRecovered: false,
        isCurrent: true,
      });
      periods.push(period);
    }

    return periods;
  }

  /**
   * Create a drawdown period object
   */
  private createDrawdownPeriod(params: {
    id: string;
    startDate: Date;
    peakDate: Date;
    troughDate: Date;
    endDate: Date | null;
    peakEquity: number;
    troughEquity: number;
    currentEquity: number;
    peakIndex: number;
    troughIndex: number;
    endIndex: number;
    isRecovered: boolean;
    isCurrent: boolean;
  }): DrawdownPeriod {
    const {
      id,
      startDate,
      peakDate,
      troughDate,
      endDate,
      peakEquity,
      troughEquity,
      currentEquity,
      peakIndex,
      troughIndex,
      endIndex,
      isRecovered,
      isCurrent,
    } = params;

    const drawdownAmount = troughEquity - peakEquity;
    const drawdownPercent = ((troughEquity - peakEquity) / peakEquity) * 100;

    const durationDays = Math.ceil(
      (troughDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24)
    );

    const recoveryDays = endDate
      ? Math.ceil((endDate.getTime() - troughDate.getTime()) / (1000 * 60 * 60 * 24))
      : null;

    // Count trades in drawdown period
    const tradesSlice = this.equityCurve.slice(peakIndex, endIndex + 1);
    const winningTrades = tradesSlice.filter(p => p.pnl > 0).length;
    const losingTrades = tradesSlice.filter(p => p.pnl < 0).length;
    const tradesInPeriod = tradesSlice.length;

    return {
      id,
      startDate: startDate.toISOString(),
      peakDate: peakDate.toISOString(),
      troughDate: troughDate.toISOString(),
      endDate: endDate ? endDate.toISOString() : null,
      peakEquity,
      troughEquity,
      currentEquity,
      drawdownAmount,
      drawdownPercent,
      durationDays,
      recoveryDays,
      isRecovered,
      isCurrent,
      tradesInPeriod,
      winningTrades,
      losingTrades,
    };
  }

  /**
   * Build time series of drawdown % over time
   */
  private buildDrawdownSeries(): TimeSeriesPoint[] {
    const series: TimeSeriesPoint[] = [];
    let peak = this.startingEquity;

    this.equityCurve.forEach(point => {
      const { timestamp, date, equity } = point;

      if (equity > peak) {
        peak = equity;
      }

      const drawdownPercent = ((equity - peak) / peak) * 100;

      series.push({
        timestamp,
        date,
        value: drawdownPercent,
        color: drawdownPercent < 0 ? '#ef4444' : '#10b981',
      });
    });

    return series;
  }

  /**
   * Find the maximum drawdown period
   */
  private findMaxDrawdown(periods: DrawdownPeriod[]): DrawdownPeriod | null {
    if (periods.length === 0) return null;

    return periods.reduce((max, period) => 
      Math.abs(period.drawdownPercent) > Math.abs(max.drawdownPercent) 
        ? period 
        : max
    );
  }

  /**
   * Find the longest drawdown period
   */
  private findLongestDrawdown(periods: DrawdownPeriod[]): DrawdownPeriod | null {
    if (periods.length === 0) return null;

    return periods.reduce((longest, period) => 
      period.durationDays > longest.durationDays 
        ? period 
        : longest
    );
  }

  /**
   * Calculate drawdown metrics at a specific point in time
   */
  public getDrawdownAtTime(timestamp: string): {
    drawdownPercent: number;
    drawdownAmount: number;
    daysInDrawdown: number;
    distanceFromPeak: number;
  } {
    const targetDate = new Date(timestamp);
    const pointIndex = this.equityCurve.findIndex(
      p => p.date.getTime() >= targetDate.getTime()
    );

    if (pointIndex === -1) {
      return {
        drawdownPercent: 0,
        drawdownAmount: 0,
        daysInDrawdown: 0,
        distanceFromPeak: 0,
      };
    }

    const currentEquity = this.equityCurve[pointIndex].equity;
    let peak = this.startingEquity;
    let peakDate: Date | null = null;

    // Find peak before this point
    for (let i = 0; i <= pointIndex; i++) {
      if (this.equityCurve[i].equity >= peak) {
        peak = this.equityCurve[i].equity;
        peakDate = this.equityCurve[i].date;
      }
    }

    const drawdownPercent = ((currentEquity - peak) / peak) * 100;
    const drawdownAmount = currentEquity - peak;
    const daysInDrawdown = peakDate
      ? Math.ceil((targetDate.getTime() - peakDate.getTime()) / (1000 * 60 * 60 * 24))
      : 0;
    const distanceFromPeak = ((peak - currentEquity) / peak) * 100;

    return {
      drawdownPercent,
      drawdownAmount,
      daysInDrawdown,
      distanceFromPeak,
    };
  }

  /**
   * Get drawdown statistics summary
   */
  public getDrawdownStats() {
    const analysis = this.analyzeDrawdowns();
    const { periods } = analysis;

    const recoveredPeriods = periods.filter(p => p.isRecovered);
    const depths = periods.map(p => Math.abs(p.drawdownPercent));
    const durations = periods.map(p => p.durationDays);
    const recoveryTimes = recoveredPeriods
      .filter(p => p.recoveryDays !== null)
      .map(p => p.recoveryDays!);

    return {
      count: periods.length,
      
      depth: {
        max: depths.length > 0 ? Math.max(...depths) : 0,
        min: depths.length > 0 ? Math.min(...depths) : 0,
        average: depths.length > 0 
          ? depths.reduce((sum, d) => sum + d, 0) / depths.length 
          : 0,
        median: this.calculateMedian(depths),
      },
      
      duration: {
        max: durations.length > 0 ? Math.max(...durations) : 0,
        min: durations.length > 0 ? Math.min(...durations) : 0,
        average: durations.length > 0 
          ? durations.reduce((sum, d) => sum + d, 0) / durations.length 
          : 0,
        median: this.calculateMedian(durations),
      },
      
      recovery: {
        max: recoveryTimes.length > 0 ? Math.max(...recoveryTimes) : 0,
        min: recoveryTimes.length > 0 ? Math.min(...recoveryTimes) : 0,
        average: recoveryTimes.length > 0 
          ? recoveryTimes.reduce((sum, t) => sum + t, 0) / recoveryTimes.length 
          : 0,
        median: this.calculateMedian(recoveryTimes),
      },
      
      recoveryRate: periods.length > 0 
        ? (recoveredPeriods.length / periods.length) * 100 
        : 0,
    };
  }

  /**
   * Calculate median of an array
   */
  private calculateMedian(values: number[]): number {
    if (values.length === 0) return 0;
    
    const sorted = [...values].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    
    return sorted.length % 2 === 0
      ? (sorted[mid - 1] + sorted[mid]) / 2
      : sorted[mid];
  }
}

// ==================== Exported Functions ====================

/**
 * Analyze drawdowns from equity curve
 */
export function analyzeDrawdowns(
  equityCurve: EquityPoint[],
  startingEquity: number = 10000
): DrawdownAnalysis {
  const analyzer = new DrawdownAnalyzer(equityCurve, startingEquity);
  return analyzer.analyzeDrawdowns();
}

/**
 * Get current drawdown status
 */
export function getCurrentDrawdown(
  equityCurve: EquityPoint[],
  startingEquity: number = 10000
): {
  isInDrawdown: boolean;
  drawdownPercent: number;
  daysInDrawdown: number;
  distanceFromPeak: number;
} {
  const analyzer = new DrawdownAnalyzer(equityCurve, startingEquity);
  const analysis = analyzer.analyzeDrawdowns();
  const current = analysis.currentDrawdown;

  if (!current) {
    return {
      isInDrawdown: false,
      drawdownPercent: 0,
      daysInDrawdown: 0,
      distanceFromPeak: 0,
    };
  }

  return {
    isInDrawdown: true,
    drawdownPercent: current.drawdownPercent,
    daysInDrawdown: current.durationDays,
    distanceFromPeak: Math.abs(current.drawdownPercent),
  };
}

/**
 * Check if equity is at all-time high
 */
export function isAtAllTimeHigh(
  equityCurve: EquityPoint[],
  tolerance: number = 0.01 // 1% tolerance
): boolean {
  if (equityCurve.length === 0) return false;

  const currentEquity = equityCurve[equityCurve.length - 1].equity;
  const maxEquity = Math.max(...equityCurve.map(p => p.equity));

  return currentEquity >= maxEquity * (1 - tolerance);
}

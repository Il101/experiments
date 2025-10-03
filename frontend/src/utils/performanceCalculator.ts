/**
 * Performance Calculator
 * Core engine for calculating trading performance metrics
 */

import type { PerformanceMetrics } from '../types/analytics';

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

// ==================== Core Calculator ====================

export class PerformanceCalculator {
  private trades: Trade[];
  private positions: Position[];
  private startingEquity: number;

  constructor(
    trades: Trade[],
    positions: Position[] = [],
    startingEquity: number = 10000
  ) {
    this.trades = trades;
    this.positions = positions;
    this.startingEquity = startingEquity;
  }

  /**
   * Calculate all performance metrics
   */
  public calculateAll(): PerformanceMetrics {
    const closedTrades = this.getClosedTrades();

    // Basic counts
    const totalTrades = closedTrades.length;
    const winners = closedTrades.filter(t => t.pnl > 0);
    const losers = closedTrades.filter(t => t.pnl < 0);
    const breakEven = closedTrades.filter(t => t.pnl === 0);

    // P&L calculations
    const realizedPnL = this.calculateRealizedPnL();
    const unrealizedPnL = this.calculateUnrealizedPnL();
    const totalPnL = realizedPnL + unrealizedPnL;
    const totalPnLPercent = (totalPnL / this.startingEquity) * 100;

    // Win/Loss metrics
    const winRate = totalTrades > 0 ? (winners.length / totalTrades) * 100 : 0;
    const lossRate = totalTrades > 0 ? (losers.length / totalTrades) * 100 : 0;

    // Average trade metrics
    const averageWin = winners.length > 0 
      ? winners.reduce((sum, t) => sum + t.pnl, 0) / winners.length 
      : 0;
    const averageLoss = losers.length > 0 
      ? losers.reduce((sum, t) => sum + t.pnl, 0) / losers.length 
      : 0;
    const averageTrade = totalTrades > 0 
      ? closedTrades.reduce((sum, t) => sum + t.pnl, 0) / totalTrades 
      : 0;

    const largestWin = winners.length > 0 
      ? Math.max(...winners.map(t => t.pnl)) 
      : 0;
    const largestLoss = losers.length > 0 
      ? Math.min(...losers.map(t => t.pnl)) 
      : 0;

    // Advanced metrics
    const profitFactor = this.calculateProfitFactor();
    const expectancy = this.calculateExpectancy();
    const sharpeRatio = this.calculateSharpeRatio();
    const sortinoRatio = this.calculateSortinoRatio();
    const calmarRatio = this.calculateCalmarRatio();
    const marRatio = this.calculateMARRatio();

    // R-Multiple analysis
    const rMultiples = closedTrades
      .filter(t => t.rMultiple !== undefined)
      .map(t => t.rMultiple!);
    const averageRMultiple = rMultiples.length > 0
      ? rMultiples.reduce((sum, r) => sum + r, 0) / rMultiples.length
      : 0;
    const bestRMultiple = rMultiples.length > 0 ? Math.max(...rMultiples) : 0;
    const worstRMultiple = rMultiples.length > 0 ? Math.min(...rMultiples) : 0;

    // Streak analysis
    const { currentStreak, longestWinStreak, longestLossStreak } = 
      this.calculateStreaks();

    // Drawdown metrics
    const drawdownMetrics = this.calculateDrawdownMetrics();

    // Risk metrics
    const { valueAtRisk95, valueAtRisk99, conditionalVaR } = 
      this.calculateRiskMetrics();
    const standardDeviation = this.calculateStandardDeviation();
    const beta = this.calculateBeta(); // Placeholder for now

    // Trade duration
    const durations = closedTrades
      .filter(t => t.exitTime)
      .map(t => this.calculateTradeDuration(t));
    const averageTradeDuration = durations.length > 0
      ? durations.reduce((sum, d) => sum + d, 0) / durations.length
      : 0;
    const shortestTrade = durations.length > 0 ? Math.min(...durations) : 0;
    const longestTrade = durations.length > 0 ? Math.max(...durations) : 0;

    // Position sizing
    const sizes = closedTrades.map(t => t.size * t.entryPrice);
    const averagePositionSize = sizes.length > 0
      ? sizes.reduce((sum, s) => sum + s, 0) / sizes.length
      : 0;
    const maxPositionSize = sizes.length > 0 ? Math.max(...sizes) : 0;
    const minPositionSize = sizes.length > 0 ? Math.min(...sizes) : 0;

    // Time period
    const dates = closedTrades
      .filter(t => t.entryTime)
      .map(t => new Date(t.entryTime));
    const startDate = dates.length > 0 
      ? new Date(Math.min(...dates.map(d => d.getTime()))).toISOString()
      : new Date().toISOString();
    const endDate = new Date().toISOString();
    const tradingDays = this.calculateTradingDays(startDate, endDate);

    // Performance grade
    const { overallGrade, gradeScore } = this.calculateGrade({
      winRate,
      profitFactor,
      sharpeRatio,
      maxDrawdown: drawdownMetrics.maxDrawdown,
      expectancy,
      recoveryFactor: drawdownMetrics.recoveryFactor,
    });

    return {
      totalPnL,
      totalPnLPercent,
      realizedPnL,
      unrealizedPnL,
      
      totalTrades,
      winningTrades: winners.length,
      losingTrades: losers.length,
      breakEvenTrades: breakEven.length,
      
      winRate,
      lossRate,
      profitFactor,
      expectancy,
      
      averageWin,
      averageLoss,
      averageTrade,
      largestWin,
      largestLoss,
      
      averageRMultiple,
      bestRMultiple,
      worstRMultiple,
      
      currentStreak,
      longestWinStreak,
      longestLossStreak,
      
      sharpeRatio,
      sortinoRatio,
      calmarRatio,
      marRatio,
      
      currentDrawdown: drawdownMetrics.currentDrawdown,
      currentDrawdownDays: drawdownMetrics.currentDrawdownDays,
      maxDrawdown: drawdownMetrics.maxDrawdown,
      maxDrawdownDays: drawdownMetrics.maxDrawdownDays,
      averageDrawdown: drawdownMetrics.averageDrawdown,
      recoveryFactor: drawdownMetrics.recoveryFactor,
      
      valueAtRisk95,
      valueAtRisk99,
      conditionalVaR,
      standardDeviation,
      beta,
      
      averageTradeDuration,
      shortestTrade,
      longestTrade,
      
      averagePositionSize,
      maxPositionSize,
      minPositionSize,
      
      startDate,
      endDate,
      tradingDays,
      
      overallGrade,
      gradeScore,
    };
  }

  // ==================== P&L Calculations ====================

  private calculateRealizedPnL(): number {
    return this.getClosedTrades().reduce((sum, t) => sum + t.pnl, 0);
  }

  private calculateUnrealizedPnL(): number {
    return this.positions.reduce((sum, p) => sum + p.unrealizedPnl, 0);
  }

  // ==================== Profit Factor ====================

  /**
   * Profit Factor = Gross Profit / Gross Loss
   * Values > 1 indicate profitability
   */
  private calculateProfitFactor(): number {
    const closedTrades = this.getClosedTrades();
    const grossProfit = closedTrades
      .filter(t => t.pnl > 0)
      .reduce((sum, t) => sum + t.pnl, 0);
    const grossLoss = Math.abs(
      closedTrades
        .filter(t => t.pnl < 0)
        .reduce((sum, t) => sum + t.pnl, 0)
    );

    return grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? Infinity : 0;
  }

  // ==================== Expectancy ====================

  /**
   * Expectancy = (Win Rate × Avg Win) - (Loss Rate × |Avg Loss|)
   * Expected value per trade
   */
  private calculateExpectancy(): number {
    const closedTrades = this.getClosedTrades();
    if (closedTrades.length === 0) return 0;

    const winners = closedTrades.filter(t => t.pnl > 0);
    const losers = closedTrades.filter(t => t.pnl < 0);

    const winRate = winners.length / closedTrades.length;
    const lossRate = losers.length / closedTrades.length;

    const averageWin = winners.length > 0
      ? winners.reduce((sum, t) => sum + t.pnl, 0) / winners.length
      : 0;
    const averageLoss = losers.length > 0
      ? Math.abs(losers.reduce((sum, t) => sum + t.pnl, 0) / losers.length)
      : 0;

    return (winRate * averageWin) - (lossRate * averageLoss);
  }

  // ==================== Sharpe Ratio ====================

  /**
   * Sharpe Ratio = (Return - Risk-free Rate) / Standard Deviation
   * Measures risk-adjusted return
   */
  private calculateSharpeRatio(riskFreeRate: number = 0): number {
    const returns = this.calculateDailyReturns();
    if (returns.length === 0) return 0;

    const averageReturn = returns.reduce((sum, r) => sum + r, 0) / returns.length;
    const stdDev = this.calculateStandardDeviation();

    return stdDev > 0 ? (averageReturn - riskFreeRate) / stdDev : 0;
  }

  // ==================== Sortino Ratio ====================

  /**
   * Sortino Ratio = (Return - Risk-free Rate) / Downside Deviation
   * Like Sharpe but only considers downside volatility
   */
  private calculateSortinoRatio(riskFreeRate: number = 0): number {
    const returns = this.calculateDailyReturns();
    if (returns.length === 0) return 0;

    const averageReturn = returns.reduce((sum, r) => sum + r, 0) / returns.length;
    const downsideReturns = returns.filter(r => r < riskFreeRate);
    
    if (downsideReturns.length === 0) return Infinity;

    const downsideDev = Math.sqrt(
      downsideReturns.reduce((sum, r) => sum + Math.pow(r - riskFreeRate, 2), 0) / 
      downsideReturns.length
    );

    return downsideDev > 0 ? (averageReturn - riskFreeRate) / downsideDev : 0;
  }

  // ==================== Calmar Ratio ====================

  /**
   * Calmar Ratio = Annualized Return / Max Drawdown
   * Higher is better
   */
  private calculateCalmarRatio(): number {
    const totalReturn = this.calculateRealizedPnL();
    const annualizedReturn = this.annualizeReturn(totalReturn);
    const maxDD = Math.abs(this.calculateDrawdownMetrics().maxDrawdown);

    return maxDD > 0 ? annualizedReturn / maxDD : annualizedReturn > 0 ? Infinity : 0;
  }

  // ==================== MAR Ratio ====================

  /**
   * MAR Ratio = Annualized Return / Average Drawdown
   */
  private calculateMARRatio(): number {
    const totalReturn = this.calculateRealizedPnL();
    const annualizedReturn = this.annualizeReturn(totalReturn);
    const avgDD = Math.abs(this.calculateDrawdownMetrics().averageDrawdown);

    return avgDD > 0 ? annualizedReturn / avgDD : annualizedReturn > 0 ? Infinity : 0;
  }

  // ==================== Drawdown Metrics ====================

  private calculateDrawdownMetrics() {
    const equityCurve = this.buildEquityCurve();
    let peak = this.startingEquity;
    let maxDD = 0;
    let maxDDDays = 0;
    let currentDD = 0;
    let currentDDDays = 0;
    let ddStart: Date | null = null;
    let totalDD = 0;
    let ddCount = 0;

    equityCurve.forEach((point, index) => {
      const equity = point.value;

      if (equity >= peak) {
        peak = equity;
        if (ddStart !== null) {
          // Drawdown recovered
          ddCount++;
          ddStart = null;
        }
      } else {
        const dd = ((equity - peak) / peak) * 100;
        totalDD += Math.abs(dd);

        if (ddStart === null) {
          ddStart = point.date;
        }

        const ddDays = Math.floor(
          (Date.now() - ddStart.getTime()) / (1000 * 60 * 60 * 24)
        );

        if (dd < maxDD) {
          maxDD = dd;
          maxDDDays = ddDays;
        }

        if (index === equityCurve.length - 1) {
          currentDD = dd;
          currentDDDays = ddDays;
        }
      }
    });

    const averageDD = ddCount > 0 ? totalDD / ddCount : 0;
    const recoveryFactor = maxDD !== 0 ? this.calculateRealizedPnL() / Math.abs(maxDD) : 0;

    return {
      currentDrawdown: currentDD,
      currentDrawdownDays: currentDDDays,
      maxDrawdown: maxDD,
      maxDrawdownDays: maxDDDays,
      averageDrawdown: averageDD,
      recoveryFactor,
    };
  }

  // ==================== Risk Metrics ====================

  private calculateRiskMetrics() {
    const returns = this.calculateDailyReturns();
    if (returns.length === 0) {
      return { valueAtRisk95: 0, valueAtRisk99: 0, conditionalVaR: 0 };
    }

    const sortedReturns = [...returns].sort((a, b) => a - b);

    // VaR at 95% confidence (5th percentile)
    const var95Index = Math.floor(returns.length * 0.05);
    const valueAtRisk95 = sortedReturns[var95Index] || 0;

    // VaR at 99% confidence (1st percentile)
    const var99Index = Math.floor(returns.length * 0.01);
    const valueAtRisk99 = sortedReturns[var99Index] || 0;

    // CVaR (average of losses beyond VaR)
    const cvarReturns = sortedReturns.slice(0, var95Index + 1);
    const conditionalVaR = cvarReturns.length > 0
      ? cvarReturns.reduce((sum, r) => sum + r, 0) / cvarReturns.length
      : 0;

    return { valueAtRisk95, valueAtRisk99, conditionalVaR };
  }

  private calculateStandardDeviation(): number {
    const returns = this.calculateDailyReturns();
    if (returns.length === 0) return 0;

    const mean = returns.reduce((sum, r) => sum + r, 0) / returns.length;
    const variance = returns.reduce((sum, r) => sum + Math.pow(r - mean, 2), 0) / returns.length;

    return Math.sqrt(variance);
  }

  private calculateBeta(): number {
    // Placeholder: would need market benchmark data
    return 1.0;
  }

  // ==================== Streak Analysis ====================

  private calculateStreaks() {
    const closedTrades = this.getClosedTrades();
    let currentStreak = 0;
    let longestWinStreak = 0;
    let longestLossStreak = 0;
    let tempWinStreak = 0;
    let tempLossStreak = 0;

    closedTrades.forEach((trade, index) => {
      const isWin = trade.pnl > 0;

      if (isWin) {
        tempWinStreak++;
        tempLossStreak = 0;
        longestWinStreak = Math.max(longestWinStreak, tempWinStreak);
      } else if (trade.pnl < 0) {
        tempLossStreak++;
        tempWinStreak = 0;
        longestLossStreak = Math.max(longestLossStreak, tempLossStreak);
      }

      if (index === closedTrades.length - 1) {
        currentStreak = isWin ? tempWinStreak : -tempLossStreak;
      }
    });

    return { currentStreak, longestWinStreak, longestLossStreak };
  }

  // ==================== Helper Functions ====================

  private getClosedTrades(): Trade[] {
    return this.trades.filter(t => t.status === 'closed' && t.exitPrice !== undefined);
  }

  private calculateDailyReturns(): number[] {
    const equityCurve = this.buildEquityCurve();
    const returns: number[] = [];

    for (let i = 1; i < equityCurve.length; i++) {
      const prevEquity = equityCurve[i - 1].value;
      const currEquity = equityCurve[i].value;
      const dailyReturn = ((currEquity - prevEquity) / prevEquity) * 100;
      returns.push(dailyReturn);
    }

    return returns;
  }

  private buildEquityCurve() {
    let equity = this.startingEquity;
    const points: { date: Date; value: number }[] = [
      { date: new Date(this.trades[0]?.entryTime || new Date()), value: equity }
    ];

    this.getClosedTrades()
      .sort((a, b) => new Date(a.exitTime!).getTime() - new Date(b.exitTime!).getTime())
      .forEach(trade => {
        equity += trade.pnl;
        points.push({
          date: new Date(trade.exitTime!),
          value: equity,
        });
      });

    return points;
  }

  private calculateTradeDuration(trade: Trade): number {
    if (!trade.exitTime) return 0;
    const entry = new Date(trade.entryTime).getTime();
    const exit = new Date(trade.exitTime).getTime();
    return (exit - entry) / (1000 * 60 * 60); // Hours
  }

  private calculateTradingDays(start: string, end: string): number {
    const startDate = new Date(start);
    const endDate = new Date(end);
    return Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24));
  }

  private annualizeReturn(totalReturn: number): number {
    const days = this.calculateTradingDays(
      this.trades[0]?.entryTime || new Date().toISOString(),
      new Date().toISOString()
    );
    const years = days / 365;
    return years > 0 ? (totalReturn / this.startingEquity) * 100 / years : 0;
  }

  private calculateGrade(metrics: {
    winRate: number;
    profitFactor: number;
    sharpeRatio: number;
    maxDrawdown: number;
    expectancy: number;
    recoveryFactor: number;
  }): { overallGrade: PerformanceMetrics['overallGrade']; gradeScore: number } {
    let score = 0;

    // Profitability (25 points)
    if (metrics.profitFactor >= 2.5) score += 25;
    else if (metrics.profitFactor >= 2.0) score += 20;
    else if (metrics.profitFactor >= 1.5) score += 15;
    else if (metrics.profitFactor >= 1.0) score += 10;
    else score += 5;

    // Consistency (25 points)
    if (metrics.winRate >= 65) score += 25;
    else if (metrics.winRate >= 55) score += 20;
    else if (metrics.winRate >= 50) score += 15;
    else if (metrics.winRate >= 45) score += 10;
    else score += 5;

    // Risk Management (25 points)
    const absDD = Math.abs(metrics.maxDrawdown);
    if (absDD <= 10) score += 25;
    else if (absDD <= 15) score += 20;
    else if (absDD <= 20) score += 15;
    else if (absDD <= 30) score += 10;
    else score += 5;

    // Efficiency (25 points)
    if (metrics.sharpeRatio >= 2.0) score += 25;
    else if (metrics.sharpeRatio >= 1.5) score += 20;
    else if (metrics.sharpeRatio >= 1.0) score += 15;
    else if (metrics.sharpeRatio >= 0.5) score += 10;
    else score += 5;

    // Determine grade
    let grade: PerformanceMetrics['overallGrade'];
    if (score >= 95) grade = 'A+';
    else if (score >= 90) grade = 'A';
    else if (score >= 85) grade = 'A-';
    else if (score >= 80) grade = 'B+';
    else if (score >= 75) grade = 'B';
    else if (score >= 70) grade = 'B-';
    else if (score >= 65) grade = 'C+';
    else if (score >= 60) grade = 'C';
    else if (score >= 55) grade = 'C-';
    else if (score >= 50) grade = 'D';
    else grade = 'F';

    return { overallGrade: grade, gradeScore: score };
  }
}

// ==================== Exported Functions ====================

export function calculatePerformanceMetrics(
  trades: Trade[],
  positions: Position[] = [],
  startingEquity: number = 10000
): PerformanceMetrics {
  const calculator = new PerformanceCalculator(trades, positions, startingEquity);
  return calculator.calculateAll();
}

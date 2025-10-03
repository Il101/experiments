/**
 * Performance Analytics Types
 * Comprehensive type definitions for trading performance metrics
 */

// ==================== Core Metrics ====================

export interface PerformanceMetrics {
  // Overall Performance
  totalPnL: number;
  totalPnLPercent: number;
  realizedPnL: number;
  unrealizedPnL: number;
  
  // Trade Statistics
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  breakEvenTrades: number;
  
  // Win/Loss Metrics
  winRate: number;                    // % of winning trades
  lossRate: number;                   // % of losing trades
  profitFactor: number;               // Gross profit / Gross loss
  expectancy: number;                 // Expected value per trade
  
  // Average Trade Metrics
  averageWin: number;
  averageLoss: number;
  averageTrade: number;
  largestWin: number;
  largestLoss: number;
  
  // R-Multiple Analysis
  averageRMultiple: number;           // Avg profit/risk ratio
  bestRMultiple: number;
  worstRMultiple: number;
  
  // Streak Analysis
  currentStreak: number;              // Positive = winning, negative = losing
  longestWinStreak: number;
  longestLossStreak: number;
  
  // Risk-Adjusted Returns
  sharpeRatio: number;                // (Return - RFR) / Std Dev
  sortinoRatio: number;               // (Return - RFR) / Downside Dev
  calmarRatio: number;                // Return / Max Drawdown
  marRatio: number;                   // Return / Avg Drawdown
  
  // Drawdown Metrics
  currentDrawdown: number;            // % from peak
  currentDrawdownDays: number;
  maxDrawdown: number;                // Worst drawdown ever
  maxDrawdownDays: number;            // Longest drawdown duration
  averageDrawdown: number;
  recoveryFactor: number;             // Net profit / Max DD
  
  // Risk Metrics
  valueAtRisk95: number;              // VaR at 95% confidence
  valueAtRisk99: number;              // VaR at 99% confidence
  conditionalVaR: number;             // CVaR (expected shortfall)
  standardDeviation: number;          // Daily returns std dev
  beta: number;                       // Market correlation (if available)
  
  // Trade Duration
  averageTradeDuration: number;       // Hours
  shortestTrade: number;
  longestTrade: number;
  
  // Position Sizing
  averagePositionSize: number;        // USD
  maxPositionSize: number;
  minPositionSize: number;
  
  // Time Period
  startDate: string;
  endDate: string;
  tradingDays: number;
  
  // Performance Grade
  overallGrade: 'A+' | 'A' | 'A-' | 'B+' | 'B' | 'B-' | 'C+' | 'C' | 'C-' | 'D' | 'F';
  gradeScore: number;                 // 0-100
}

// ==================== Drawdown Analysis ====================

export interface DrawdownPeriod {
  id: string;
  startDate: string;
  peakDate: string;
  troughDate: string;
  endDate: string | null;             // null if not recovered
  
  peakEquity: number;
  troughEquity: number;
  currentEquity: number;
  
  drawdownAmount: number;             // Absolute loss
  drawdownPercent: number;            // % decline from peak
  
  durationDays: number;               // Days in drawdown
  recoveryDays: number | null;        // Days to recover (null if ongoing)
  
  isRecovered: boolean;
  isCurrent: boolean;
  
  tradesInPeriod: number;
  winningTrades: number;
  losingTrades: number;
}

export interface DrawdownAnalysis {
  periods: DrawdownPeriod[];
  
  currentDrawdown: DrawdownPeriod | null;
  maxDrawdown: DrawdownPeriod | null;
  longestDrawdown: DrawdownPeriod | null;
  
  averageDrawdownPercent: number;
  averageDrawdownDuration: number;
  averageRecoveryTime: number;
  
  totalDrawdowns: number;
  recoveredDrawdowns: number;
  ongoingDrawdowns: number;
  
  drawdownSeries: TimeSeriesPoint[];  // For charting
}

// ==================== Trade Statistics ====================

export interface TradeStatistics {
  // Distribution
  pnlDistribution: {
    bins: number[];                   // P&L ranges
    counts: number[];                 // Frequency
    mean: number;
    median: number;
    mode: number;
    stdDev: number;
    skewness: number;
    kurtosis: number;
  };
  
  // Duration Analysis
  durationStats: {
    averageHours: number;
    medianHours: number;
    distribution: {
      bins: string[];                 // Time ranges (e.g., "0-1h", "1-4h")
      counts: number[];
    };
  };
  
  // Size Analysis
  sizeStats: {
    averageUsd: number;
    medianUsd: number;
    distribution: {
      bins: number[];                 // Size ranges
      counts: number[];
    };
  };
  
  // Timing Analysis
  timingStats: {
    bestHour: number;                 // 0-23
    worstHour: number;
    bestDayOfWeek: number;            // 0-6 (Sun-Sat)
    worstDayOfWeek: number;
    hourlyPerformance: HourlyPerformance[];
    dailyPerformance: DailyPerformance[];
  };
  
  // Symbol Analysis
  symbolStats: SymbolPerformance[];
  
  // Exit Quality
  exitQuality: {
    averageEfficiency: number;        // % of optimal exit captured
    optimalExits: number;             // Count of near-perfect exits
    prematureExits: number;           // Exited too early
    lateExits: number;                // Exited too late
  };
}

export interface HourlyPerformance {
  hour: number;                       // 0-23
  trades: number;
  totalPnL: number;
  averagePnL: number;
  winRate: number;
}

export interface DailyPerformance {
  dayOfWeek: number;                  // 0-6 (Sun-Sat)
  dayName: string;
  trades: number;
  totalPnL: number;
  averagePnL: number;
  winRate: number;
}

export interface SymbolPerformance {
  symbol: string;
  trades: number;
  winningTrades: number;
  losingTrades: number;
  winRate: number;
  totalPnL: number;
  averagePnL: number;
  profitFactor: number;
  sharpeRatio: number;
  maxDrawdown: number;
  averageRMultiple: number;
  totalVolume: number;                // Total USD traded
}

// ==================== Time Series Data ====================

export interface TimeSeriesPoint {
  timestamp: string;                  // ISO date
  date: Date;
  value: number;
  
  // Optional metadata
  label?: string;
  color?: string;
  metadata?: Record<string, any>;
}

export interface EquityCurveData {
  points: TimeSeriesPoint[];
  
  startingEquity: number;
  currentEquity: number;
  peakEquity: number;
  troughEquity: number;
  
  totalReturn: number;
  totalReturnPercent: number;
  
  // Annotations for key events
  peaks: TimeSeriesPoint[];           // Local peaks
  troughs: TimeSeriesPoint[];         // Local troughs
  trades: TradeAnnotation[];          // Trade markers
}

export interface TradeAnnotation {
  timestamp: string;
  type: 'entry' | 'exit';
  symbol: string;
  side: 'long' | 'short';
  pnl?: number;
  rMultiple?: number;
}

// ==================== Date Range ====================

export interface DateRange {
  start: Date;
  end: Date;
  label: string;
  preset: DateRangePreset;
}

export type DateRangePreset = 
  | '7D'
  | '30D'
  | '90D'
  | 'YTD'
  | '1Y'
  | 'ALL'
  | 'CUSTOM';

// ==================== Performance Grade ====================

export interface PerformanceGrade {
  overall: 'A+' | 'A' | 'A-' | 'B+' | 'B' | 'B-' | 'C+' | 'C' | 'C-' | 'D' | 'F';
  score: number;                      // 0-100
  
  breakdown: {
    profitability: number;            // /25 points
    consistency: number;              // /25 points
    riskManagement: number;           // /25 points
    efficiency: number;               // /25 points
  };
  
  strengths: string[];
  weaknesses: string[];
  suggestions: string[];
}

// ==================== Comparison ====================

export interface PerformanceComparison {
  current: PerformanceMetrics;
  previous: PerformanceMetrics;
  
  changes: {
    totalPnL: number;
    winRate: number;
    profitFactor: number;
    sharpeRatio: number;
    maxDrawdown: number;
  };
  
  percentChanges: {
    totalPnL: number;
    winRate: number;
    profitFactor: number;
    sharpeRatio: number;
    maxDrawdown: number;
  };
  
  trend: 'improving' | 'declining' | 'stable';
}

// ==================== Chart Data ====================

export interface ChartDataset {
  id: string;
  label: string;
  data: TimeSeriesPoint[];
  color: string;
  type: 'line' | 'area' | 'bar' | 'scatter';
  yAxisId?: string;
}

export interface ChartConfig {
  title: string;
  datasets: ChartDataset[];
  xAxisLabel?: string;
  yAxisLabel?: string;
  showLegend?: boolean;
  showGrid?: boolean;
  showTooltip?: boolean;
  height?: number;
}

// ==================== Utility Types ====================

export interface MetricDefinition {
  key: keyof PerformanceMetrics;
  label: string;
  description: string;
  format: 'number' | 'percent' | 'currency' | 'ratio' | 'grade';
  decimals: number;
  goodDirection: 'higher' | 'lower' | 'neutral';
  benchmark?: number;
  tooltip?: string;
}

export interface MetricCard {
  metric: MetricDefinition;
  value: number;
  previousValue?: number;
  change?: number;
  percentChange?: number;
  trend?: 'up' | 'down' | 'flat';
  status?: 'good' | 'warning' | 'bad';
}

// ==================== Export Types ====================

export interface AnalyticsExport {
  metadata: {
    exportDate: string;
    dateRange: DateRange;
    totalTrades: number;
    version: string;
  };
  
  metrics: PerformanceMetrics;
  drawdowns: DrawdownAnalysis;
  statistics: TradeStatistics;
  equityCurve: EquityCurveData;
  
  format: 'json' | 'csv' | 'pdf';
}

// ==================== Constants ====================

export const METRIC_DEFINITIONS: Record<string, MetricDefinition> = {
  totalPnL: {
    key: 'totalPnL',
    label: 'Total P&L',
    description: 'Total profit/loss including open positions',
    format: 'currency',
    decimals: 2,
    goodDirection: 'higher',
    tooltip: 'Sum of all realized and unrealized P&L',
  },
  winRate: {
    key: 'winRate',
    label: 'Win Rate',
    description: 'Percentage of winning trades',
    format: 'percent',
    decimals: 1,
    goodDirection: 'higher',
    benchmark: 50,
    tooltip: 'Winning trades / Total trades × 100',
  },
  profitFactor: {
    key: 'profitFactor',
    label: 'Profit Factor',
    description: 'Ratio of gross profit to gross loss',
    format: 'ratio',
    decimals: 2,
    goodDirection: 'higher',
    benchmark: 1.5,
    tooltip: 'Gross profit / Gross loss. Values > 1 indicate profitability',
  },
  sharpeRatio: {
    key: 'sharpeRatio',
    label: 'Sharpe Ratio',
    description: 'Risk-adjusted return metric',
    format: 'ratio',
    decimals: 2,
    goodDirection: 'higher',
    benchmark: 1.0,
    tooltip: '(Return - Risk-free rate) / Standard deviation. Higher is better',
  },
  maxDrawdown: {
    key: 'maxDrawdown',
    label: 'Max Drawdown',
    description: 'Largest peak-to-trough decline',
    format: 'percent',
    decimals: 1,
    goodDirection: 'lower',
    tooltip: 'Maximum % decline from equity peak',
  },
};

export const DATE_RANGE_PRESETS: DateRange[] = [
  { start: new Date(), end: new Date(), label: 'Last 7 Days', preset: '7D' },
  { start: new Date(), end: new Date(), label: 'Last 30 Days', preset: '30D' },
  { start: new Date(), end: new Date(), label: 'Last 90 Days', preset: '90D' },
  { start: new Date(), end: new Date(), label: 'Year to Date', preset: 'YTD' },
  { start: new Date(), end: new Date(), label: 'Last Year', preset: '1Y' },
  { start: new Date(), end: new Date(), label: 'All Time', preset: 'ALL' },
];

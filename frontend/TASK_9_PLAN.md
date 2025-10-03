# Task 9: Performance Analytics Dashboard - PLAN

**Duration:** 1 week (35-40 hours)  
**UX Impact:** +4 points (143 → 147/100)  
**Priority:** HIGH  
**Status:** 🏗️ IN PROGRESS

---

## 📋 Overview

Build a comprehensive performance analytics dashboard that calculates and visualizes key trading metrics:
- Win rate, profit factor, Sharpe ratio, expectancy
- Drawdown analysis (current, max, recovery time)
- Trade distribution (winners/losers histogram)
- Time-based performance (daily, weekly, monthly)
- Symbol-based performance comparison
- Risk-adjusted returns
- Advanced statistics (Sortino, Calmar, MAR)

---

## 🎯 Phase Breakdown

### Phase 1: Core Metrics Engine (Day 1-2, 12 hours)

**Files to create:**
1. `types/analytics.ts` (150 lines)
   - PerformanceMetrics interface
   - DrawdownAnalysis interface
   - TradeStatistics interface
   - TimeSeriesData interface

2. `utils/performanceCalculator.ts` (400 lines)
   - `calculateWinRate()` - Winners / Total trades
   - `calculateProfitFactor()` - Gross profit / Gross loss
   - `calculateExpectancy()` - Average win × win rate - Average loss × loss rate
   - `calculateSharpeRatio()` - (Return - Risk-free rate) / Std deviation
   - `calculateSortinoRatio()` - Downside deviation only
   - `calculateMaxDrawdown()` - Largest peak-to-trough decline
   - `calculateRecoveryTime()` - Time to recover from drawdown

3. `utils/drawdownAnalyzer.ts` (250 lines)
   - `findDrawdownPeriods()` - Identify all DD periods
   - `calculateDrawdownMetrics()` - Duration, depth, recovery
   - `getDrawdownSeries()` - Time series for charting

4. `hooks/usePerformanceMetrics.ts` (200 lines)
   - React Query hook for metrics calculation
   - Memoization for expensive calculations
   - Refresh on trade updates

**Deliverables:**
- Type-safe metrics calculation engine
- Real-time metrics updates
- Historical analysis support

---

### Phase 2: Visualization Components (Day 3-4, 12 hours)

**Files to create:**
5. `components/analytics/MetricsOverview.tsx` (300 lines)
   - Key metrics cards (Win rate, PF, Sharpe)
   - Color-coded indicators (green/red)
   - Comparison with benchmarks
   - Tooltips with explanations

6. `components/analytics/EquityCurveChart.tsx` (350 lines)
   - Recharts line chart
   - Cumulative P&L over time
   - Drawdown overlay (shaded areas)
   - Zoom & pan functionality

7. `components/analytics/DrawdownChart.tsx` (250 lines)
   - Underwater equity curve
   - Peak markers
   - Recovery periods highlighted

8. `components/analytics/TradeDistributionChart.tsx` (200 lines)
   - Histogram of P&L results
   - Normal distribution overlay
   - Outlier identification

9. `components/analytics/PerformanceHeatmap.tsx` (250 lines)
   - Calendar heatmap (daily returns)
   - Month/day grid
   - Color intensity based on P&L

10. `components/analytics/SymbolPerformanceChart.tsx` (200 lines)
    - Bar chart comparing symbols
    - Win rate, profit, trade count per symbol
    - Sort by various metrics

**Deliverables:**
- 6 interactive chart components
- Responsive design
- Dark mode support
- Tooltip-rich visualizations

---

### Phase 3: Advanced Analytics (Day 5, 8 hours)

**Files to create:**
11. `utils/riskMetrics.ts` (300 lines)
    - `calculateVaR()` - Value at Risk (95%, 99%)
    - `calculateCVaR()` - Conditional VaR
    - `calculateBeta()` - Market correlation
    - `calculateCalmarRatio()` - Return / Max DD
    - `calculateMAR()` - Minimum Acceptable Return

12. `utils/tradeAnalyzer.ts` (250 lines)
    - `analyzeTradeDuration()` - Avg hold time, distribution
    - `analyzeTradeSize()` - Position sizing patterns
    - `analyzeEntryTiming()` - Time of day/week analysis
    - `analyzeExitQuality()` - How close to optimal exit

13. `components/analytics/RiskMetricsPanel.tsx` (200 lines)
    - VaR/CVaR display
    - Risk-adjusted return metrics
    - Position concentration analysis

14. `components/analytics/TradeTimingAnalysis.tsx` (200 lines)
    - Best/worst hours/days
    - Seasonality patterns
    - Time-based filtering

**Deliverables:**
- Advanced risk metrics
- Trade timing insights
- Risk-adjusted performance

---

### Phase 4: Dashboard Integration (Day 6-7, 8 hours)

**Files to create:**
15. `pages/AnalyticsPage.tsx` (400 lines)
    - Main analytics dashboard
    - Tab navigation (Overview, Drawdown, Symbols, Risk)
    - Date range selector
    - Export functionality

16. `components/analytics/DateRangeSelector.tsx` (150 lines)
    - Preset ranges (7D, 30D, 90D, YTD, All)
    - Custom range picker
    - Comparison mode (vs previous period)

17. `components/analytics/PerformanceSummary.tsx` (250 lines)
    - Executive summary card
    - Key highlights (best/worst)
    - Overall grade (A-F based on metrics)

18. `components/analytics/index.ts` (20 lines)
    - Component exports

**Deliverables:**
- Fully integrated dashboard
- Multi-tab layout
- Export to PDF/PNG

---

## 📊 Metrics to Calculate

### Core Metrics
- [x] Total P&L (realized + unrealized)
- [x] Win Rate (% winning trades)
- [x] Profit Factor (gross profit / gross loss)
- [x] Average Win / Average Loss
- [x] Expectancy (expected value per trade)
- [x] Total Trades (count)
- [x] Winning Trades / Losing Trades

### Risk-Adjusted Returns
- [x] Sharpe Ratio (return / volatility)
- [x] Sortino Ratio (return / downside volatility)
- [x] Calmar Ratio (return / max drawdown)
- [x] MAR Ratio (return / average drawdown)

### Drawdown Analysis
- [x] Current Drawdown (% from peak)
- [x] Maximum Drawdown (worst decline)
- [x] Average Drawdown
- [x] Drawdown Duration (current)
- [x] Max Drawdown Duration (longest)
- [x] Recovery Factor (net profit / max DD)

### Trade Statistics
- [x] Average Trade Duration
- [x] Best Trade / Worst Trade
- [x] Longest Winning Streak
- [x] Longest Losing Streak
- [x] Average R-Multiple
- [x] Consecutive Wins/Losses

### Risk Metrics
- [x] Value at Risk (VaR 95%, 99%)
- [x] Conditional VaR (CVaR)
- [x] Standard Deviation (daily returns)
- [x] Beta (vs benchmark)
- [x] Max Position Size
- [x] Average Position Size

### Time-Based Analysis
- [x] Daily Returns
- [x] Weekly Returns
- [x] Monthly Returns
- [x] Best Day / Worst Day
- [x] Best Hour / Worst Hour
- [x] Day of Week Performance

---

## 🎨 UI Components Breakdown

### Overview Tab
```
┌─────────────────────────────────────────────┐
│ Performance Summary Card                    │
│ - Grade: A (85/100)                         │
│ - Key Highlights                            │
└─────────────────────────────────────────────┘

┌────────────┬────────────┬────────────┬──────┐
│ Win Rate   │ Profit     │ Sharpe     │ Max  │
│ 65.3%      │ Factor     │ Ratio      │ DD   │
│ +2.3% ↑    │ 2.45       │ 1.82       │-12.3%│
└────────────┴────────────┴────────────┴──────┘

┌─────────────────────────────────────────────┐
│ Equity Curve Chart                          │
│ [Interactive line chart with drawdown]      │
└─────────────────────────────────────────────┘

┌──────────────────────┬──────────────────────┐
│ Trade Distribution   │ Performance Heatmap  │
│ [Histogram]          │ [Calendar grid]      │
└──────────────────────┴──────────────────────┘
```

### Drawdown Tab
```
┌─────────────────────────────────────────────┐
│ Drawdown Metrics                            │
│ - Current DD: -5.2% (12 days)               │
│ - Max DD: -12.3% (45 days, recovered)       │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Underwater Equity Chart                     │
│ [Area chart showing DD depth over time]     │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Drawdown Periods Table                      │
│ Start | End | Depth | Duration | Recovery   │
└─────────────────────────────────────────────┘
```

### Symbols Tab
```
┌─────────────────────────────────────────────┐
│ Symbol Performance Comparison               │
│ [Bar chart with multiple metrics]           │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Symbol Stats Table                          │
│ Symbol | Trades | Win Rate | P&L | Sharpe   │
└─────────────────────────────────────────────┘
```

### Risk Tab
```
┌────────────┬────────────┬────────────┬──────┐
│ VaR 95%    │ VaR 99%    │ Std Dev    │ Beta │
│ -$1,234    │ -$2,456    │ 2.3%       │ 0.85 │
└────────────┴────────────┴────────────┴──────┘

┌─────────────────────────────────────────────┐
│ Risk-Adjusted Returns                       │
│ [Comparison chart]                          │
└─────────────────────────────────────────────┘
```

---

## 🧪 Testing Strategy

### Unit Tests
- [ ] Metrics calculation accuracy
- [ ] Drawdown detection logic
- [ ] Edge cases (0 trades, all wins, all losses)
- [ ] Date range filtering

### Integration Tests
- [ ] Chart rendering with real data
- [ ] Date range selector updates charts
- [ ] Export functionality
- [ ] Performance with 1000+ trades

### Manual Tests
- [ ] Visual regression testing
- [ ] Responsive design (mobile/tablet)
- [ ] Dark mode consistency
- [ ] Tooltip accuracy

---

## 📈 Success Criteria

- [ ] 20+ performance metrics calculated
- [ ] 6+ interactive charts
- [ ] Real-time updates on trade changes
- [ ] Date range filtering (7D, 30D, 90D, YTD, All)
- [ ] Symbol-level breakdown
- [ ] Export to PDF/PNG
- [ ] Performance < 100ms for 1000 trades
- [ ] Mobile responsive
- [ ] Dark mode support
- [ ] Comprehensive tooltips

---

## 💡 Implementation Notes

### Performance Optimization
1. **Memoization:** Cache expensive calculations
2. **Incremental Updates:** Only recalculate changed metrics
3. **Web Workers:** Offload heavy calculations
4. **Lazy Loading:** Load charts on demand
5. **Virtualization:** For large trade lists

### Data Requirements
- Closed trades with P&L
- Open positions with unrealized P&L
- Trade timestamps (entry/exit)
- Position sizes
- Risk amounts (stop loss)

### Dependencies
- `recharts` - For all charts
- `date-fns` - Date calculations
- `lodash` - Statistical functions
- `react-to-pdf` - PDF export (optional)

---

## 🚀 Next Steps

**Day 1 (Today):**
1. Create type definitions (`types/analytics.ts`)
2. Build core calculator (`utils/performanceCalculator.ts`)
3. Create drawdown analyzer (`utils/drawdownAnalyzer.ts`)
4. Build React hook (`hooks/usePerformanceMetrics.ts`)

**Estimated:** 12 hours (Day 1-2)

Ready to start? 🎯

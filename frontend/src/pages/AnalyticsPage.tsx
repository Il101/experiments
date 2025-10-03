/**
 * AnalyticsPage Component
 * Main analytics dashboard with tab navigation
 */

import React, { useState } from 'react';
import { Download, BarChart3, TrendingDown, Target, Shield } from 'lucide-react';
import type { DateRange } from '../types/analytics';
import { usePerformanceMetrics } from '../hooks/usePerformanceMetrics';
import {
  MetricsOverview,
  PerformanceSummaryCard,
  EquityCurveChart,
  DrawdownChart,
  TradeDistributionChart,
  PerformanceHeatmap,
  SymbolPerformanceChart,
  DateRangeSelector,
} from '../components/analytics';

// ==================== Interfaces ====================

type TabId = 'overview' | 'drawdown' | 'symbols' | 'distribution';

interface Tab {
  id: TabId;
  label: string;
  icon: React.ReactNode;
}

// ==================== Component ====================

export const AnalyticsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [dateRange, setDateRange] = useState<DateRange>({
    start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // 30 days ago
    end: new Date(),
    label: 'Last 30 Days',
    preset: '30D',
  });

  // Fetch performance metrics
  // TODO: Replace with actual data fetching from API
  const trades: any[] = []; // Will be replaced with actual Trade[] from API
  const positions: any[] = []; // Will be replaced with actual Position[] from API
  
  const { 
    metrics, 
    drawdowns, 
    equityCurve, 
    isLoading 
  } = usePerformanceMetrics({
    trades,
    positions,
    startingEquity: 10000,
  });

  // Convert equity curve to TimeSeriesPoint format
  const equityCurveData = equityCurve.map(point => ({
    timestamp: point.timestamp,
    date: new Date(point.timestamp),
    value: point.equity,
  }));

  // Tabs configuration
  const tabs: Tab[] = [
    { id: 'overview', label: 'Overview', icon: <BarChart3 className="w-4 h-4" /> },
    { id: 'drawdown', label: 'Drawdown', icon: <TrendingDown className="w-4 h-4" /> },
    { id: 'symbols', label: 'Symbols', icon: <Target className="w-4 h-4" /> },
    { id: 'distribution', label: 'Distribution', icon: <Shield className="w-4 h-4" /> },
  ];

  // Export functionality (placeholder)
  const handleExport = () => {
    console.log('Exporting analytics data...');
    // TODO: Implement PDF/CSV export
  };

  if (isLoading || !metrics || !drawdowns) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Loading analytics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <div className="container mx-auto px-4 py-6 max-w-7xl">
        {/* Page Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                Performance Analytics
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Comprehensive trading performance analysis
              </p>
            </div>

            <div className="flex items-center gap-3">
              {/* Date Range Selector */}
              <DateRangeSelector
                value={dateRange}
                onChange={setDateRange}
              />

              {/* Export Button */}
              <button
                onClick={handleExport}
                className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
              >
                <Download className="w-4 h-4" />
                <span className="text-sm font-medium">Export</span>
              </button>
            </div>
          </div>

          {/* Performance Summary Card */}
          <PerformanceSummaryCard metrics={metrics} />
        </div>

        {/* Tabs Navigation */}
        <div className="mb-6">
          <div className="border-b border-gray-200 dark:border-gray-700">
            <nav className="flex gap-4">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                      : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
                  }`}
                >
                  {tab.icon}
                  <span className="font-medium">{tab.label}</span>
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* Tab Content */}
        <div className="space-y-6">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <>
              {/* Metrics Grid */}
              <MetricsOverview metrics={metrics} />

              {/* Equity Curve */}
              <EquityCurveChart
                data={equityCurveData}
                startingEquity={10000}
                showDrawdown={true}
                showBrush={true}
              />

              {/* Bottom Row: Distribution + Heatmap */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <TradeDistributionChart
                  trades={trades.map(t => ({
                    id: t.id,
                    pnl: t.pnl,
                    pnlPercent: t.pnlPercent,
                  }))}
                />

                <PerformanceHeatmap
                  dailyReturns={[]} // TODO: Calculate from trades
                />
              </div>
            </>
          )}

          {/* Drawdown Tab */}
          {activeTab === 'drawdown' && (
            <>
              <DrawdownChart
                drawdownSeries={drawdowns.drawdownSeries}
                drawdownPeriods={drawdowns.periods}
              />

              {/* Drawdown Stats Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                    Drawdown Summary
                  </h3>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">Total Periods:</span>
                      <span className="font-semibold text-gray-900 dark:text-gray-100">
                        {drawdowns.totalDrawdowns}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">Recovered:</span>
                      <span className="font-semibold text-green-600 dark:text-green-400">
                        {drawdowns.recoveredDrawdowns}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">Ongoing:</span>
                      <span className="font-semibold text-orange-600 dark:text-orange-400">
                        {drawdowns.ongoingDrawdowns}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">Avg Duration:</span>
                      <span className="font-semibold text-gray-900 dark:text-gray-100">
                        {drawdowns.averageDrawdownDuration.toFixed(0)} days
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400">Avg Recovery:</span>
                      <span className="font-semibold text-gray-900 dark:text-gray-100">
                        {drawdowns.averageRecoveryTime.toFixed(0)} days
                      </span>
                    </div>
                  </div>
                </div>

                <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                    Current Status
                  </h3>
                  {drawdowns.currentDrawdown ? (
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Current DD:</span>
                        <span className="font-semibold text-red-600 dark:text-red-400">
                          {drawdowns.currentDrawdown.drawdownPercent.toFixed(2)}%
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Days in DD:</span>
                        <span className="font-semibold text-gray-900 dark:text-gray-100">
                          {drawdowns.currentDrawdown.durationDays}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Peak Equity:</span>
                        <span className="font-semibold text-gray-900 dark:text-gray-100">
                          ${drawdowns.currentDrawdown.peakEquity.toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Current Equity:</span>
                        <span className="font-semibold text-gray-900 dark:text-gray-100">
                          ${drawdowns.currentDrawdown.currentEquity.toFixed(2)}
                        </span>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-green-600 dark:text-green-400">
                      ✓ No active drawdown - trading at or near peak equity
                    </p>
                  )}
                </div>

                <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                    Max Drawdown
                  </h3>
                  {drawdowns.maxDrawdown && (
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Depth:</span>
                        <span className="font-semibold text-red-600 dark:text-red-400">
                          {drawdowns.maxDrawdown.drawdownPercent.toFixed(2)}%
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Duration:</span>
                        <span className="font-semibold text-gray-900 dark:text-gray-100">
                          {drawdowns.maxDrawdown.durationDays} days
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Recovery:</span>
                        <span className="font-semibold text-gray-900 dark:text-gray-100">
                          {drawdowns.maxDrawdown.recoveryDays 
                            ? `${drawdowns.maxDrawdown.recoveryDays} days` 
                            : 'Ongoing'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Started:</span>
                        <span className="font-semibold text-gray-900 dark:text-gray-100">
                          {new Date(drawdowns.maxDrawdown.startDate).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}

          {/* Symbols Tab */}
          {activeTab === 'symbols' && (
            <>
              <SymbolPerformanceChart
                symbolStats={[]} // TODO: Calculate from trades
              />
            </>
          )}

          {/* Distribution Tab */}
          {activeTab === 'distribution' && (
            <>
              <TradeDistributionChart
                trades={trades.map(t => ({
                  id: t.id,
                  pnl: t.pnl,
                  pnlPercent: t.pnlPercent,
                }))}
                binCount={15}
                height={450}
              />

              <PerformanceHeatmap
                dailyReturns={[]} // TODO: Calculate from trades
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
};

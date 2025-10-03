/**
 * Real-Time Trading Dashboard Page
 * Displays live P&L, position heat map, and risk exposure
 */

import React from 'react';
import { Activity, TrendingUp, AlertCircle } from 'lucide-react';
import { usePositions } from '../hooks';
import { LivePnL, PositionHeatMap, RiskExposureChart } from '../components/dashboard';
import { Card } from '../components/ui/Card';

export const RealTimeDashboardPage: React.FC = () => {
  const { data: positions = [], isLoading, error } = usePositions();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Activity className="w-12 h-12 animate-spin text-blue-500 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading trading data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="max-w-md">
          <div className="text-center p-6">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
              Failed to Load Data
            </h3>
            <p className="text-gray-600 dark:text-gray-400 text-sm">
              {error instanceof Error ? error.message : 'Unknown error occurred'}
            </p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <div className="container mx-auto px-4 py-6 max-w-7xl">
        {/* Page Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                Real-Time Dashboard
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Live position tracking with P&L updates, heat maps, and risk analysis
              </p>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="space-y-6">
          {/* Top Row: Live P&L */}
          <LivePnL positions={positions} />

          {/* Middle Row: Heat Map */}
          <PositionHeatMap positions={positions} />

          {/* Bottom Row: Risk Exposure */}
          <RiskExposureChart positions={positions} />

          {/* Info Card */}
          {positions.length === 0 && (
            <Card className="text-center py-12">
              <div className="max-w-md mx-auto">
                <Activity className="w-16 h-16 text-gray-300 dark:text-gray-700 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                  No Active Positions
                </h3>
                <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">
                  Start trading to see real-time P&L updates, position heat maps, and risk analysis.
                </p>
                <div className="flex justify-center gap-3">
                  <a
                    href="/trading"
                    className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
                  >
                    Go to Trading
                  </a>
                  <a
                    href="/scanner"
                    className="px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg transition-colors"
                  >
                    Scan for Signals
                  </a>
                </div>
              </div>
            </Card>
          )}
        </div>

        {/* Feature Info Banner */}
        <div className="mt-8 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-white" />
              </div>
            </div>
            <div className="flex-1">
              <h4 className="font-semibold text-blue-900 dark:text-blue-100 mb-1">
                Real-Time Tracking Features
              </h4>
              <ul className="text-sm text-blue-700 dark:text-blue-300 space-y-1">
                <li>• <strong>Live P&L Updates:</strong> Automatic price tracking via WebSocket with millisecond precision</li>
                <li>• <strong>Position Heat Map:</strong> Visual representation of winners/losers with color-coded intensity</li>
                <li>• <strong>Risk Exposure Analysis:</strong> Monitor stop-loss distances and portfolio balance</li>
                <li>• <strong>R-Multiple Tracking:</strong> See risk-adjusted returns in real-time for each position</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

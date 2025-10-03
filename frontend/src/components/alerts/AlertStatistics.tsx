/**
 * AlertStatistics Component
 * Display alert statistics and analytics
 */

import React from 'react';
import {
  TrendingUp,
  Bell,
  BellOff,
  Zap,
  Clock,
  CheckCircle,
  XCircle,
} from 'lucide-react';
import { useAlertStore } from '../../store/useAlertStore';

// ==================== Component ====================

export const AlertStatistics: React.FC = () => {
  const { getStatistics, triggers } = useAlertStore();
  const stats = getStatistics();

  const statCards = [
    {
      label: 'Total Alerts',
      value: stats.totalAlerts,
      icon: Bell,
      color: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
      change: null,
    },
    {
      label: 'Active Alerts',
      value: stats.activeAlerts,
      icon: CheckCircle,
      color: 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400',
      change: null,
    },
    {
      label: 'Inactive Alerts',
      value: stats.inactiveAlerts,
      icon: BellOff,
      color: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400',
      change: null,
    },
    {
      label: 'Total Triggers',
      value: stats.totalTriggers,
      icon: Zap,
      color: 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400',
      change: null,
    },
    {
      label: 'Triggers Today',
      value: stats.triggersToday,
      icon: Clock,
      color: 'bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400',
      change: null,
    },
    {
      label: 'Success Rate',
      value: `${stats.successRate.toFixed(1)}%`,
      icon: TrendingUp,
      color: 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400',
      change: null,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {statCards.map((stat) => (
          <div
            key={stat.label}
            className="p-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg"
          >
            <div className="flex items-start justify-between mb-3">
              <div className={`p-2 rounded-lg ${stat.color}`}>
                <stat.icon className="w-5 h-5" />
              </div>
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-1">
              {stat.value}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              {stat.label}
            </div>
          </div>
        ))}
      </div>

      {/* Most Triggered Alerts */}
      {stats.mostTriggered.length > 0 && (
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Most Triggered Alerts
          </h3>
          <div className="space-y-3">
            {stats.mostTriggered.map((alert, index) => (
              <div
                key={alert.alertId}
                className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <div className="flex items-center justify-center w-8 h-8 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full text-sm font-semibold">
                    {index + 1}
                  </div>
                  <div>
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      {alert.alertName}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      Triggered {alert.triggerCount} time{alert.triggerCount !== 1 ? 's' : ''}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-bold text-blue-600 dark:text-blue-400">
                    {alert.triggerCount}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Activity */}
      {stats.recentTriggers.length > 0 && (
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Recent Activity
          </h3>
          <div className="space-y-3">
            {stats.recentTriggers.map((trigger) => (
              <div
                key={trigger.id}
                className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
              >
                <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                  <Zap className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">
                    {trigger.alertName}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                    {new Date(trigger.triggeredAt).toLocaleString()}
                  </div>
                  <div className="flex items-center gap-2">
                    {trigger.actionsExecuted.map((action, idx) => (
                      <span
                        key={idx}
                        className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs ${
                          action.success
                            ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                            : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                        }`}
                      >
                        {action.success ? (
                          <CheckCircle className="w-3 h-3" />
                        ) : (
                          <XCircle className="w-3 h-3" />
                        )}
                        {action.actionType}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {triggers.length === 0 && (
        <div className="text-center py-12">
          <Clock className="w-12 h-12 text-gray-400 dark:text-gray-600 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">
            No trigger history yet. Alerts will appear here once triggered.
          </p>
        </div>
      )}
    </div>
  );
};
